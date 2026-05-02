from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import decode_token
from app.db.session import get_db
from app.schemas.chat import MessageRequest
from app.services.persistent_chat_service import PersistentChatService
from app.services.thread_service import ThreadService

router = APIRouter(prefix="/api/threads/{thread_id}/messages", tags=["chat"])
chat_service = PersistentChatService()
thread_service = ThreadService()


def _get_current_user_id(token: str | None = None) -> UUID:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No token provided")

    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing user ID")

    try:
        return UUID(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user ID in token")


@router.post("")
async def send_message(
    thread_id: UUID,
    payload: MessageRequest,
    token: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    user_id = _get_current_user_id(token)

    # Verify thread ownership
    thread = await thread_service.get_thread_by_id(db, thread_id, user_id)
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

    message = payload.message.strip()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "validation_error", "message": "Message cannot be empty."},
        )

    return StreamingResponse(
        chat_service.stream_chat_with_persistence(db, thread_id, user_id, message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
