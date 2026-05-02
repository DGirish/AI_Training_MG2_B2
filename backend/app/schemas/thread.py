from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    content: str = Field(min_length=1)
    role: str


class MessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    created_at: datetime

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
