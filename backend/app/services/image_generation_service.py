from __future__ import annotations

import asyncio
import base64
from io import BytesIO
from uuid import UUID

from openai import OpenAIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm import get_litellm_openai_client
from app.core.config import settings
from app.models.models import Attachment
from app.services.attachment_service import AttachmentService

try:
    from PIL import Image
except Exception:  # pragma: no cover - optional at import time during partial installs
    Image = None


IMAGE_PROMPT_PREFIXES = (
    "/image ",
    "generate an image",
    "generate image",
    "create an image",
    "create image",
    "draw ",
    "illustrate ",
)


class ImageGenerationService:
    def __init__(self) -> None:
        self.attachment_service = AttachmentService()

    @staticmethod
    def is_image_request(message: str, explicit_flag: bool = False) -> bool:
        if explicit_flag:
            return True
        normalized = message.strip().lower()
        return normalized.startswith(IMAGE_PROMPT_PREFIXES)

    async def generate_and_persist(
        self,
        db: AsyncSession,
        *,
        thread_id: UUID,
        user_id: UUID,
        source_message_id: UUID,
        prompt: str,
        user_context: str,
    ) -> Attachment:
        client = get_litellm_openai_client()

        try:
            response = await asyncio.to_thread(
                client.images.generate,
                model=settings.image_gen_model,
                prompt=prompt,
                size="1024x1024",
                extra_body={
                    "metadata": {
                        "application": settings.app_name,
                        "environment": settings.environment,
                        "user_email": user_context,
                    }
                },
            )
        except OpenAIError as exc:  # pragma: no cover - exercised through route behavior
            raise ValueError(f"Image generation failed: {exc}") from exc

        image_data = getattr(response, "data", None) or []
        if not image_data:
            raise ValueError("Image generation returned no data")

        first_image = image_data[0]
        b64_json = getattr(first_image, "b64_json", None)
        image_url = getattr(first_image, "url", None)

        if not b64_json:
            raise ValueError(f"Image generation did not return base64 data (url={image_url!r})")

        image_bytes = base64.b64decode(b64_json)
        width, height = self._detect_dimensions(image_bytes)

        return await self.attachment_service.create_generated_image_attachment(
            db,
            thread_id=thread_id,
            user_id=user_id,
            source_message_id=source_message_id,
            prompt=prompt,
            model_name=settings.image_gen_model,
            image_bytes=image_bytes,
            mime_type="image/png",
            file_name="generated-image.png",
            width=width,
            height=height,
        )

    @staticmethod
    def _detect_dimensions(image_bytes: bytes) -> tuple[int | None, int | None]:
        if Image is None:
            return None, None

        try:
            with Image.open(BytesIO(image_bytes)) as image:
                return image.width, image.height
        except Exception:
            return None, None
