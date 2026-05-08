from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import decode_token
from app.db.session import get_db
from app.schemas.attachment import AttachmentResponse, UploadAttachmentsResponse
from app.services.attachment_service import AttachmentService, UploadedAttachmentFile


router = APIRouter(prefix="/api/chat/attachments", tags=["attachments"])
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


@router.post("/upload")
async def upload_attachments(
    thread_id: UUID,
    files: Annotated[list[UploadFile], File(...)],
    token: str | None = None,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
) -> UploadAttachmentsResponse:
    user_id = _get_current_user_id(token)

    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files provided")

    payloads: list[UploadedAttachmentFile] = []
    for file in files:
        if not file.filename:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filename required")

        content = await file.read()
        payloads.append(
            UploadedAttachmentFile(
                filename=file.filename,
                content=content,
                mime_type=file.content_type or "application/octet-stream",
            )
        )

    try:
        attachments = await attachment_service.upload_attachments(db, thread_id, user_id, payloads)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return UploadAttachmentsResponse(
        attachment_ids=[attachment.id for attachment in attachments],
        attachments=[AttachmentResponse.model_validate(attachment) for attachment in attachments],
    )


@router.delete("/{attachment_id}")
async def delete_attachment(
    attachment_id: UUID,
    token: str | None = None,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
) -> dict[str, str]:
    user_id = _get_current_user_id(token)
    deleted = await attachment_service.delete_attachment(db, attachment_id, user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

    return {"status": "deleted"}


@router.get("/{attachment_id}/content")
async def get_attachment_content(
    attachment_id: UUID,
    token: str | None = None,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
) -> Response:
    user_id = _get_current_user_id(token)
    attachment = await attachment_service.get_attachment(db, attachment_id, user_id)
    if attachment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

    try:
        content = await attachment_service.get_attachment_bytes(attachment)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    return Response(content=content, media_type=attachment.mime_type)
