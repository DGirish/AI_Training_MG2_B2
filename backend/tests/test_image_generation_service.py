from __future__ import annotations

import base64
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.core.config import settings
from app.services.image_generation_service import ImageGenerationService


class ImageGenerationServiceTests(unittest.IsolatedAsyncioTestCase):
    def test_image_request_detection(self) -> None:
        self.assertTrue(ImageGenerationService.is_image_request("Generate an image of a sunrise"))
        self.assertTrue(ImageGenerationService.is_image_request("Tell me a joke", explicit_flag=True))
        self.assertFalse(ImageGenerationService.is_image_request("Tell me a joke"))

    async def test_generate_and_persist_uses_required_model_and_persists_metadata(self) -> None:
        service = ImageGenerationService()
        service.attachment_service.create_generated_image_attachment = AsyncMock(return_value="attachment")
        fake_response = SimpleNamespace(data=[SimpleNamespace(b64_json=base64.b64encode(b"png-bytes").decode("ascii"))])
        fake_client = SimpleNamespace(images=SimpleNamespace(generate=lambda **_: fake_response))

        with patch("app.services.image_generation_service.get_litellm_openai_client", return_value=fake_client):
            with patch.object(service, "_detect_dimensions", return_value=(1024, 1024)):
                result = await service.generate_and_persist(
                    db=AsyncMock(),
                    thread_id=uuid4(),
                    user_id=uuid4(),
                    source_message_id=uuid4(),
                    prompt="Generate an image of a blue bird",
                    user_context="user@example.com",
                )

        self.assertEqual(result, "attachment")
        service.attachment_service.create_generated_image_attachment.assert_awaited_once()
        kwargs = service.attachment_service.create_generated_image_attachment.await_args.kwargs
        self.assertEqual(kwargs["model_name"], settings.image_gen_model)
        self.assertEqual(kwargs["prompt"], "Generate an image of a blue bird")
        self.assertEqual(kwargs["mime_type"], "image/png")
        self.assertEqual(kwargs["width"], 1024)
        self.assertEqual(kwargs["height"], 1024)


if __name__ == "__main__":
    unittest.main()
