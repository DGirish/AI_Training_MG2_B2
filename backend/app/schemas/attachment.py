from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime


class AttachmentResponse(BaseModel):
    id: UUID
    user_id: UUID
    thread_id: UUID
    source_message_id: UUID | None = None
    message_id: UUID | None
    original_filename: str
    stored_filename: str
    storage_path: str
    public_url: str | None
    mime_type: str
    file_size: int
    attachment_type: str
    storage_bucket: str | None = None
    model_name: str | None = None
    prompt: str | None = None
    width: int | None = None
    height: int | None = None
    generation_status: str | None = None
    generation_error: str | None = None
    indexed_status: str = "not_indexed"
    indexed_at: datetime | None = None
    chunk_count: int = 0
    indexing_error: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class UploadAttachmentsResponse(BaseModel):
    attachment_ids: list[UUID]
    attachments: list[AttachmentResponse]


class MessageWithAttachments(BaseModel):
    message: str = Field(min_length=1, max_length=10000)
    attachment_ids: list[UUID] = Field(default_factory=list)
