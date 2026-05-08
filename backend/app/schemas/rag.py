from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RagIngestPdfRequest(BaseModel):
    thread_id: UUID
    attachment_id: UUID


class RagIngestPdfResponse(BaseModel):
    attachment_id: UUID
    indexed_status: str
    chunk_count: int


class RagChatRequest(BaseModel):
    thread_id: UUID
    attachment_id: UUID
    question: str = Field(min_length=1, max_length=10000)


class RagSource(BaseModel):
    attachment_id: UUID
    chunk_index: int
    score: float | None = None
    excerpt: str


class RagChatResponse(BaseModel):
    answer: str
    sources: list[RagSource]
    created_at: datetime
