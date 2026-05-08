from __future__ import annotations

from datetime import datetime
from uuid import uuid4, UUID

from sqlalchemy import ARRAY, DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Table name constants to avoid duplication
PROFILES_TABLE = "profiles"
CHAT_THREADS_TABLE = "chat_threads"
CHAT_MESSAGES_TABLE = "chat_messages"
CHAT_ATTACHMENTS_TABLE = "chat_attachments"


class Base(DeclarativeBase):
    pass


class Profile(Base):
    __tablename__ = PROFILES_TABLE

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    threads: Mapped[list["ChatThread"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class ChatThread(Base):
    __tablename__ = CHAT_THREADS_TABLE

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey(f"{PROFILES_TABLE}.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[Profile] = relationship(back_populates="threads")
    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="thread", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = CHAT_MESSAGES_TABLE

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    thread_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey(f"{CHAT_THREADS_TABLE}.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey(f"{PROFILES_TABLE}.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    attachment_ids: Mapped[list[UUID] | None] = mapped_column(ARRAY(Uuid(as_uuid=True)), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    thread: Mapped[ChatThread] = relationship(back_populates="messages")
    user: Mapped[Profile] = relationship()
    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="message",
        foreign_keys="Attachment.message_id",
    )


class Attachment(Base):
    __tablename__ = CHAT_ATTACHMENTS_TABLE

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    thread_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey(f"{CHAT_THREADS_TABLE}.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey(f"{PROFILES_TABLE}.id", ondelete="CASCADE"), nullable=False
    )
    source_message_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey(f"{CHAT_MESSAGES_TABLE}.id", ondelete="SET NULL"), nullable=True
    )
    message_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey(f"{CHAT_MESSAGES_TABLE}.id", ondelete="CASCADE"), nullable=True
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    public_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(nullable=False)
    attachment_type: Mapped[str] = mapped_column(String(50), nullable=False)
    storage_bucket: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    generation_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    generation_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    indexed_status: Mapped[str] = mapped_column(String(50), nullable=False, default="not_indexed")
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    indexing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    thread: Mapped[ChatThread] = relationship()
    user: Mapped[Profile] = relationship()
    message: Mapped[ChatMessage | None] = relationship(
        back_populates="attachments",
        foreign_keys=[message_id],
    )
