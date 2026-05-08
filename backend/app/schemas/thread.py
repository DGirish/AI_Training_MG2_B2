from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.attachment import AttachmentResponse


class MessageCreate(BaseModel):
    content: str = Field(min_length=1)
    role: str


class MessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    attachment_ids: list[UUID] = Field(default_factory=list)
    attachments: list[AttachmentResponse] = Field(default_factory=list)
    created_at: datetime

    @field_validator("attachment_ids", mode="before")
    @classmethod
    def _coerce_attachment_ids(cls, value):
        return value or []

    @field_validator("attachments", mode="before")
    @classmethod
    def _coerce_attachments(cls, value):
        return value or []

    class Config:
        from_attributes = True


class ThreadResponse(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ThreadCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class ThreadUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
