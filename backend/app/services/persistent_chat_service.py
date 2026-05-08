from __future__ import annotations

import json
from typing import AsyncIterator
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.chains.chat_chain import build_chat_chain
from app.core.config import settings
from app.models.models import ChatMessage
from app.services.attachment_service import AttachmentService
from app.services.image_generation_service import ImageGenerationService
from app.services.thread_service import ThreadService


def _sse(event: str, data: dict[str, str]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=True)}\n\n"


class PersistentChatService:
    def __init__(self):
        self.thread_service = ThreadService()
        self.attachment_service = AttachmentService()
        self.image_generation_service = ImageGenerationService()

    async def get_recent_thread_memory(
        self,
        db: AsyncSession,
        thread_id: UUID,
        user_id: UUID,
        limit: int = 5,
    ) -> list[ChatMessage]:
        message_limit = max(0, limit) * 2
        if message_limit == 0:
            return []

        stmt = (
            select(ChatMessage)
            .where(
                ChatMessage.thread_id == thread_id,
                ChatMessage.user_id == user_id,
                ChatMessage.role.in_(["user", "assistant"]),
            )
            .order_by(desc(ChatMessage.created_at))
            .limit(message_limit)
        )
        result = await db.execute(stmt)
        messages = result.scalars().all()
        messages.reverse()
        return messages

    @staticmethod
    def _format_history(messages: list[ChatMessage]) -> str:
        if not messages:
            return ""

        role_labels = {"user": "User", "assistant": "Assistant"}
        lines: list[str] = []
        for message in messages:
            label = role_labels.get(message.role, message.role.title())
            lines.append(f"{label}: {message.content}")
        return "\n\n".join(lines)

    async def stream_chat_with_persistence(
        self,
        db: AsyncSession,
        thread_id: UUID,
        user_id: UUID,
        message: str,
        attachment_ids: list[UUID] | None = None,
        generate_image: bool = False,
    ) -> AsyncIterator[str]:
        chain = build_chat_chain()
        metadata = {
            "application": settings.app_name,
            "environment": settings.environment,
        }

        user_context = settings.litellm_user_id or str(user_id)
        attachment_ids = attachment_ids or []

        try:
            memory_messages = await self.get_recent_thread_memory(db, thread_id, user_id, limit=5)
            history = self._format_history(memory_messages)

            # Save user message with attachment IDs
            user_msg = await self.thread_service.add_message(
                db, thread_id, user_id, "user", message, attachment_ids=attachment_ids
            )

            # Persist attachment linkage before LLM call.
            if attachment_ids:
                await self.attachment_service.link_attachments_to_message(
                    db=db,
                    attachment_ids=attachment_ids,
                    thread_id=thread_id,
                    message_id=user_msg.id,
                    user_id=user_id,
                )

            attachment_context = await self.attachment_service.build_attachment_context(
                db=db,
                attachment_ids=attachment_ids,
                user_id=user_id,
            )

            # Auto-name default threads based on the first user message.
            await self.thread_service.maybe_name_thread_from_first_user_message(
                db,
                thread_id,
                user_id,
                message,
            )

            if self.image_generation_service.is_image_request(message, explicit_flag=generate_image):
                generated_attachment = await self.image_generation_service.generate_and_persist(
                    db,
                    thread_id=thread_id,
                    user_id=user_id,
                    source_message_id=user_msg.id,
                    prompt=message,
                    user_context=user_context,
                )

                assistant_text = f"Generated an image for: {message}"
                assistant_message = await self.thread_service.add_message(
                    db,
                    thread_id,
                    user_id,
                    "assistant",
                    assistant_text,
                    attachment_ids=[generated_attachment.id],
                )
                await self.attachment_service.link_attachments_to_message(
                    db=db,
                    attachment_ids=[generated_attachment.id],
                    thread_id=thread_id,
                    message_id=assistant_message.id,
                    user_id=user_id,
                )
                yield _sse("token", {"token": assistant_text})
                yield _sse("done", {"status": "complete"})
                return

            # Stream tokens from LLM
            full_response = ""
            async for token in chain.astream(
                {
                    "history": history,
                    "input": message,
                    "attachment_context": attachment_context,
                },
                config={
                    "metadata": {
                        "user_email": user_context,
                        **metadata,
                    }
                },
            ):
                if token:
                    full_response += token
                    yield _sse("token", {"token": token})

            # Save assistant response
            await self.thread_service.add_message(
                db, thread_id, user_id, "assistant", full_response
            )

            yield _sse("done", {"status": "complete"})
        except Exception as exc:
            yield _sse("error", {"message": str(exc)})
