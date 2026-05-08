from __future__ import annotations

import json
from typing import AsyncIterator

from app.ai.chains.chat_chain import build_chat_chain
from app.core.config import settings


def _sse(event: str, data: dict[str, str]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=True)}\n\n"


class ChatService:
    async def stream_chat(self, message: str) -> AsyncIterator[str]:
        chain = build_chat_chain()
        metadata = {
            "application": settings.app_name,
            "environment": settings.environment,
        }

        # Include configured user id when available so proxy usage attribution is preserved.
        user_context = settings.litellm_user_id or "anonymous"

        try:
            async for token in chain.astream(
                {"history": "", "input": message},
                config={
                    "metadata": {
                        "user_email": user_context,
                        **metadata,
                    }
                },
            ):
                if token:
                    yield _sse("token", {"token": token})

            yield _sse("done", {"status": "complete"})
        except Exception as exc:
            yield _sse("error", {"message": str(exc)})
