from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.chat import ChatRequest
from app.services.chat_service import ChatService


router = APIRouter(prefix="/api", tags=["chat"])
service = ChatService()


@router.post(
    "/chat",
    responses={
        400: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "error": "validation_error",
                            "message": "Message cannot be empty.",
                        }
                    }
                }
            },
        }
    },
)
async def chat(payload: ChatRequest) -> StreamingResponse:
    message = payload.message.strip()
    if not message:
        raise HTTPException(
            status_code=400,
            detail={"error": "validation_error", "message": "Message cannot be empty."},
        )

    return StreamingResponse(
        service.stream_chat(message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
