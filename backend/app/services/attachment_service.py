from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4
import mimetypes

import aiofiles
import pandas as pd
from pypdf import PdfReader
from sqlalchemy import Select, text, select
from sqlalchemy.ext.asyncio import AsyncSession
from supabase import Client, create_client

from app.core.config import settings
from app.models.models import Attachment, ChatThread


@dataclass(frozen=True)
class UploadedAttachmentFile:
    filename: str
    content: bytes
    mime_type: str


MIME_TEXT_CSV = "text/csv"
MIME_TEXT_PREFIX = "text/"


ATTACHMENT_TYPE_BY_PREFIX: dict[str, str] = {
    "image/": "image",
    "video/": "video",
    "application/pdf": "pdf",
    MIME_TEXT_CSV: "table",
    "application/vnd.ms-excel": "table",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "table",
    "text/plain": "text",
    MIME_TEXT_PREFIX: "code",
    "application/json": "code",
    "application/xml": "code",
    "application/javascript": "code",
    "text/markdown": "text",
}

ALLOWED_MIME_TYPES: set[str] = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "video/mp4",
    "video/quicktime",
    "video/mpeg",
    "application/pdf",
    MIME_TEXT_CSV,
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain",
    "text/markdown",
    "text/x-python",
    "text/x-java-source",
    "text/javascript",
    "application/json",
}


class AttachmentService:
    _schema_ready = False
    _bucket_ready = False
    _schema_lock: asyncio.Lock = asyncio.Lock()

    def __init__(self) -> None:
        self._supabase_client: Client | None = None

    async def _ensure_schema(self, db: AsyncSession) -> None:
        if self._schema_ready:
            return

        async with self._schema_lock:
            if self._schema_ready:
                return

            await db.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS public.chat_attachments (
                        id uuid PRIMARY KEY,
                        user_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
                        thread_id uuid NOT NULL REFERENCES public.chat_threads(id) ON DELETE CASCADE,
                        source_message_id uuid NULL REFERENCES public.chat_messages(id) ON DELETE SET NULL,
                        message_id uuid NULL REFERENCES public.chat_messages(id) ON DELETE CASCADE,
                        original_filename varchar(255) NOT NULL,
                        stored_filename varchar(255) NOT NULL,
                        storage_path varchar(512) NOT NULL UNIQUE,
                        public_url varchar(1024) NULL,
                        mime_type varchar(100) NOT NULL,
                        file_size integer NOT NULL,
                        attachment_type varchar(50) NOT NULL,
                        storage_bucket varchar(255) NULL,
                        model_name varchar(255) NULL,
                        prompt text NULL,
                        width integer NULL,
                        height integer NULL,
                        generation_status varchar(50) NULL,
                        generation_error text NULL,
                        indexed_status text NOT NULL DEFAULT 'not_indexed',
                        indexed_at timestamptz NULL,
                        chunk_count integer NOT NULL DEFAULT 0,
                        indexing_error text NULL,
                        created_at timestamptz NOT NULL DEFAULT now()
                    )
                    """
                )
            )
            await db.execute(text("ALTER TABLE public.chat_attachments ADD COLUMN IF NOT EXISTS source_message_id uuid NULL"))
            await db.execute(text("ALTER TABLE public.chat_attachments ADD COLUMN IF NOT EXISTS storage_bucket varchar(255) NULL"))
            await db.execute(text("ALTER TABLE public.chat_attachments ADD COLUMN IF NOT EXISTS model_name varchar(255) NULL"))
            await db.execute(text("ALTER TABLE public.chat_attachments ADD COLUMN IF NOT EXISTS prompt text NULL"))
            await db.execute(text("ALTER TABLE public.chat_attachments ADD COLUMN IF NOT EXISTS width integer NULL"))
            await db.execute(text("ALTER TABLE public.chat_attachments ADD COLUMN IF NOT EXISTS height integer NULL"))
            await db.execute(text("ALTER TABLE public.chat_attachments ADD COLUMN IF NOT EXISTS generation_status varchar(50) NULL"))
            await db.execute(text("ALTER TABLE public.chat_attachments ADD COLUMN IF NOT EXISTS generation_error text NULL"))
            await db.execute(text("ALTER TABLE public.chat_attachments ADD COLUMN IF NOT EXISTS indexed_status text NOT NULL DEFAULT 'not_indexed'"))
            await db.execute(text("ALTER TABLE public.chat_attachments ADD COLUMN IF NOT EXISTS indexed_at timestamptz NULL"))
            await db.execute(text("ALTER TABLE public.chat_attachments ADD COLUMN IF NOT EXISTS chunk_count integer NOT NULL DEFAULT 0"))
            await db.execute(text("ALTER TABLE public.chat_attachments ADD COLUMN IF NOT EXISTS indexing_error text NULL"))
            await db.execute(
                text(
                    "ALTER TABLE public.chat_messages "
                    "ADD COLUMN IF NOT EXISTS attachment_ids uuid[] NULL"
                )
            )
            await db.commit()
            self._schema_ready = True

    @staticmethod
    def _classify_attachment_type(mime_type: str, filename: str) -> str:
        if mime_type in ATTACHMENT_TYPE_BY_PREFIX:
            return ATTACHMENT_TYPE_BY_PREFIX[mime_type]

        for prefix, attachment_type in ATTACHMENT_TYPE_BY_PREFIX.items():
            if prefix.endswith("/") and mime_type.startswith(prefix):
                return attachment_type

        guessed_type, _ = mimetypes.guess_type(filename)
        if guessed_type and guessed_type.startswith("text/"):
            return "text"

        return "code"

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        clean = "".join(ch for ch in filename if ch.isalnum() or ch in {"-", "_", "."})
        return clean or "attachment"

    @staticmethod
    def _build_local_storage_path(user_id: UUID, thread_id: UUID, stored_filename: str) -> Path:
        upload_root = Path(settings.upload_dir)
        return upload_root / str(user_id) / str(thread_id) / stored_filename

    def _get_supabase_client(self) -> Client:
        if self._supabase_client is not None:
            return self._supabase_client

        if not settings.resolved_supabase_url:
            raise ValueError("SUPABASE_URL could not be resolved for storage operations")
        if not settings.supabase_service_role_key:
            raise ValueError("SUPABASE_SERVICE_ROLE_KEY is required for storage operations")

        self._supabase_client = create_client(
            settings.resolved_supabase_url,
            settings.supabase_service_role_key,
        )
        return self._supabase_client

    async def _ensure_storage_bucket(self) -> None:
        if self._bucket_ready:
            return

        client = self._get_supabase_client()

        def ensure_bucket() -> None:
            try:
                buckets = client.storage.list_buckets()
                if any(bucket.name == settings.supabase_storage_bucket for bucket in buckets):
                    return
                client.storage.create_bucket(
                    settings.supabase_storage_bucket,
                    options={"public": False, "file_size_limit": str(settings.max_upload_mb * 1024 * 1024)},
                )
            except Exception:
                # If the bucket already exists or the admin API reports a benign conflict, uploads can proceed.
                return

        await asyncio.to_thread(ensure_bucket)
        self._bucket_ready = True

    @staticmethod
    async def _write_file(path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(path, "wb") as target:
            await target.write(content)

    @staticmethod
    async def _read_text(path: Path, limit_chars: int = 12000) -> str:
        async with aiofiles.open(path, "r", encoding="utf-8", errors="ignore") as source:
            content = await source.read(limit_chars + 1)
        return content[:limit_chars]

    def _validate_upload(self, upload: UploadedAttachmentFile) -> tuple[str, int]:
        mime_type = upload.mime_type or mimetypes.guess_type(upload.filename)[0] or "application/octet-stream"
        if mime_type not in ALLOWED_MIME_TYPES and not mime_type.startswith(MIME_TEXT_PREFIX):
            raise ValueError(f"Unsupported file type: {mime_type}")

        file_size = len(upload.content)
        max_upload_bytes = settings.max_upload_mb * 1024 * 1024
        if file_size > max_upload_bytes:
            raise ValueError(f"File exceeds max upload size ({settings.max_upload_mb} MB)")

        return mime_type, file_size

    async def _ensure_thread_access(self, db: AsyncSession, thread_id: UUID, user_id: UUID) -> None:
        stmt: Select[tuple[ChatThread]] = select(ChatThread).where(
            ChatThread.id == thread_id,
            ChatThread.user_id == user_id,
        )
        result = await db.execute(stmt)
        if result.scalars().first() is None:
            raise ValueError("Thread not found or not owned by user")

    async def upload_attachments(
        self,
        db: AsyncSession,
        thread_id: UUID,
        user_id: UUID,
        files: list[UploadedAttachmentFile],
    ) -> list[Attachment]:
        await self._ensure_schema(db)
        await self._ensure_thread_access(db, thread_id, user_id)

        created: list[Attachment] = []

        for upload in files:
            if not upload.filename:
                raise ValueError("Filename is required")

            mime_type, file_size = self._validate_upload(upload)
            attachment_type = self._classify_attachment_type(mime_type, upload.filename)

            original_filename = self._sanitize_filename(upload.filename)
            stored_filename = f"{uuid4().hex}_{original_filename}"
            storage_path = self._build_local_storage_path(user_id, thread_id, stored_filename)

            await self._write_file(storage_path, upload.content)

            attachment = Attachment(
                id=uuid4(),
                user_id=user_id,
                thread_id=thread_id,
                source_message_id=None,
                message_id=None,
                original_filename=original_filename,
                stored_filename=stored_filename,
                storage_path=str(storage_path),
                public_url=None,
                mime_type=mime_type,
                file_size=file_size,
                attachment_type=attachment_type,
                storage_bucket=None,
                model_name=None,
                prompt=None,
                width=None,
                height=None,
                generation_status=None,
                generation_error=None,
            )
            db.add(attachment)
            created.append(attachment)

        await db.commit()
        for attachment in created:
            await db.refresh(attachment)

        return created

    async def get_attachment(self, db: AsyncSession, attachment_id: UUID, user_id: UUID) -> Attachment | None:
        await self._ensure_schema(db)
        stmt = select(Attachment).where(
            Attachment.id == attachment_id,
            Attachment.user_id == user_id,
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def delete_attachment(self, db: AsyncSession, attachment_id: UUID, user_id: UUID) -> bool:
        attachment = await self.get_attachment(db, attachment_id, user_id)
        if attachment is None:
            return False

        if attachment.storage_bucket:
            client = self._get_supabase_client()
            await asyncio.to_thread(
                client.storage.from_(attachment.storage_bucket).remove,
                [attachment.storage_path],
            )
        else:
            Path(attachment.storage_path).unlink(missing_ok=True)

        await db.delete(attachment)
        await db.commit()
        return True

    async def link_attachments_to_message(
        self,
        db: AsyncSession,
        attachment_ids: list[UUID],
        thread_id: UUID,
        message_id: UUID,
        user_id: UUID,
    ) -> list[Attachment]:
        await self._ensure_schema(db)
        linked: list[Attachment] = []

        for attachment_id in attachment_ids:
            attachment = await self.get_attachment(db, attachment_id, user_id)
            if attachment is None:
                continue
            if attachment.thread_id != thread_id:
                continue
            attachment.message_id = message_id
            linked.append(attachment)

        await db.commit()
        return linked

    async def build_attachment_context(
        self,
        db: AsyncSession,
        attachment_ids: list[UUID],
        user_id: UUID,
    ) -> str:
        if not attachment_ids:
            return ""

        context_blocks: list[str] = []
        for attachment_id in attachment_ids:
            attachment = await self.get_attachment(db, attachment_id, user_id)
            if attachment is None:
                continue
            block = await self._extract_context(attachment)
            if block:
                context_blocks.append(block)

        return "\n\n".join(context_blocks)

    async def create_generated_image_attachment(
        self,
        db: AsyncSession,
        *,
        thread_id: UUID,
        user_id: UUID,
        source_message_id: UUID,
        prompt: str,
        model_name: str,
        image_bytes: bytes,
        mime_type: str,
        file_name: str,
        width: int | None = None,
        height: int | None = None,
        generation_error: str | None = None,
    ) -> Attachment:
        await self._ensure_schema(db)
        await self._ensure_thread_access(db, thread_id, user_id)
        await self._ensure_storage_bucket()

        stored_filename = self._sanitize_filename(file_name)
        storage_path = f"generated/{user_id}/{thread_id}/{uuid4().hex}_{stored_filename}"
        client = self._get_supabase_client()

        await asyncio.to_thread(
            client.storage.from_(settings.supabase_storage_bucket).upload,
            storage_path,
            image_bytes,
            {"content-type": mime_type, "upsert": "false"},
        )

        attachment = Attachment(
            id=uuid4(),
            user_id=user_id,
            thread_id=thread_id,
            source_message_id=source_message_id,
            message_id=None,
            original_filename=stored_filename,
            stored_filename=stored_filename,
            storage_path=storage_path,
            public_url=None,
            mime_type=mime_type,
            file_size=len(image_bytes),
            attachment_type="generated_image",
            storage_bucket=settings.supabase_storage_bucket,
            model_name=model_name,
            prompt=prompt,
            width=width,
            height=height,
            generation_status="ready" if generation_error is None else "failed",
            generation_error=generation_error,
        )
        db.add(attachment)
        await db.commit()
        await db.refresh(attachment)
        return attachment

    async def get_attachment_bytes(self, attachment: Attachment) -> bytes:
        if attachment.storage_bucket:
            client = self._get_supabase_client()
            return await asyncio.to_thread(
                client.storage.from_(attachment.storage_bucket).download,
                attachment.storage_path,
            )

        file_path = Path(attachment.storage_path)
        async with aiofiles.open(file_path, "rb") as source:
            return await source.read()

    async def _extract_context(self, attachment: Attachment) -> str:
        if attachment.storage_bucket:
            return (
                f"Attachment ({attachment.attachment_type}): {attachment.original_filename}\n"
                f"Prompt: {attachment.prompt or 'n/a'}\n"
                f"Model: {attachment.model_name or 'n/a'}"
            )

        file_path = Path(attachment.storage_path)
        if not file_path.exists():
            return ""

        if attachment.attachment_type in {"image", "video", "generated_image"}:
            return (
                f"Attachment ({attachment.attachment_type}): {attachment.original_filename}\n"
                f"Mime: {attachment.mime_type}\n"
                f"Size: {attachment.file_size} bytes\n"
                "Content extraction: metadata only"
            )

        if attachment.attachment_type == "pdf":
            reader = PdfReader(str(file_path))
            texts: list[str] = []
            for page in reader.pages[:10]:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    texts.append(page_text.strip())
            pdf_text = "\n".join(texts)[:12000]
            return f"Attachment (pdf): {attachment.original_filename}\n{pdf_text}"

        if attachment.attachment_type == "table":
            if attachment.mime_type == MIME_TEXT_CSV:
                frame = pd.read_csv(file_path)
            else:
                frame = pd.read_excel(file_path)

            summary = [
                f"rows={len(frame)}",
                f"columns={list(frame.columns)}",
                "sample:",
                frame.head(5).to_string(index=False),
            ]
            return f"Attachment (table): {attachment.original_filename}\n" + "\n".join(summary)

        text_content = await self._read_text(file_path)
        label = "code" if attachment.attachment_type == "code" else "text"
        return f"Attachment ({label}): {attachment.original_filename}\n{text_content}"
