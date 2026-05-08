from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import decode_token
from app.db.session import get_db
from app.schemas.rag import RagChatRequest, RagChatResponse, RagIngestPdfRequest, RagIngestPdfResponse, RagSource
from app.services.attachment_service import AttachmentService
from app.services.rag_service import RagService


router = APIRouter(prefix="/api/rag", tags=["rag"])
rag_service = RagService()
attachment_service = AttachmentService()


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


@router.post("/ingest-pdf")
async def ingest_pdf(
    payload: RagIngestPdfRequest,
    token: str | None = None,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
) -> RagIngestPdfResponse:
    user_id = _get_current_user_id(token)

    try:
        attachment, chunk_count = await rag_service.ingest_pdf(
            db,
            thread_id=payload.thread_id,
            attachment_id=payload.attachment_id,
            user_id=user_id,
            attachment_bytes_loader=attachment_service.get_attachment_bytes,
        )
        return RagIngestPdfResponse(
            attachment_id=attachment.id,
            indexed_status=attachment.indexed_status,
            chunk_count=chunk_count,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/chat")
async def rag_chat(
    payload: RagChatRequest,
    token: str | None = None,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
) -> RagChatResponse:
    user_id = _get_current_user_id(token)

    try:
        answer, sources_payload = await rag_service.ask_pdf(
            db,
            thread_id=payload.thread_id,
            attachment_id=payload.attachment_id,
            user_id=user_id,
            question=payload.question.strip(),
        )

        sources = [RagSource(**source) for source in sources_payload]
        return RagChatResponse(answer=answer, sources=sources, created_at=datetime.now(timezone.utc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
