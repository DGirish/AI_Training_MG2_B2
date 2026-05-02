from __future__ import annotations

import json
from typing import AsyncIterator
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.chains.chat_chain import build_chat_chain
from app.core.config import settings
from app.services.thread_service import ThreadService


def _sse(event: str, data: dict[str, str]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=True)}\n\n"


class PersistentChatService:
    def __init__(self):
        self.thread_service = ThreadService()

    async def stream_chat_with_persistence(
        self,
        db: AsyncSession,
        thread_id: UUID,
        user_id: UUID,
        message: str,
    ) -> AsyncIterator[str]:
        chain = build_chat_chain()
        metadata = {
            "application": settings.app_name,
            "environment": settings.environment,
        }

        user_context = settings.litellm_user_id or str(user_id)

        try:
            # Save user message
            await self.thread_service.add_message(db, thread_id, user_id, "user", message)

            # Auto-name default threads based on the first user message.
            await self.thread_service.maybe_name_thread_from_first_user_message(
                db,
                thread_id,
                user_id,
                message,
            )

            # Stream tokens from LLM
            full_response = ""
            async for token in chain.astream(
                {"user_message": message},
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
            await self.thread_service.add_message(db, thread_id, user_id, "assistant", full_response)

            yield _sse("done", {"status": "complete"})
        except Exception as exc:
            yield _sse("error", {"message": str(exc)})
