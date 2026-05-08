from __future__ import annotations

import io
from datetime import datetime, timezone
from uuid import UUID

import chromadb
from chromadb.api.models.Collection import Collection
from pypdf import PdfReader
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm import get_litellm_openai_client
from app.core.config import settings
from app.models.models import Attachment, ChatMessage, ChatThread
from app.services.thread_service import ThreadService


class RagService:
    def __init__(self) -> None:
        self.thread_service = ThreadService()
        self._chroma_client: chromadb.PersistentClient | None = None

    def _get_chroma_client(self) -> chromadb.PersistentClient:
        if self._chroma_client is not None:
            return self._chroma_client

        persist_dir = settings.chroma_persist_dir or "./chroma_db"
        self._chroma_client = chromadb.PersistentClient(path=persist_dir)
        return self._chroma_client

    def _get_collection(self, user_id: UUID) -> Collection:
        client = self._get_chroma_client()
        collection_name = f"user_{user_id}_rag"
        return client.get_or_create_collection(name=collection_name)

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = 1200, overlap: int = 200) -> list[str]:
        normalized = " ".join(text.split())
        if not normalized:
            return []

        chunks: list[str] = []
        start = 0
        text_len = len(normalized)

        while start < text_len:
            end = min(start + chunk_size, text_len)
            chunk = normalized[start:end]
            if chunk:
                chunks.append(chunk)
            if end >= text_len:
                break
            start = max(0, end - overlap)

        return chunks

    @staticmethod
    def _extract_pdf_text(pdf_bytes: bytes) -> str:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        pages_text: list[str] = []
        for page in reader.pages:
            text = page.extract_text() or ""
            stripped = text.strip()
            if stripped:
                pages_text.append(stripped)
        return "\n\n".join(pages_text)

    async def _get_owned_thread(self, db: AsyncSession, thread_id: UUID, user_id: UUID) -> ChatThread | None:
        return await self.thread_service.get_thread_by_id(db, thread_id, user_id)

    async def _get_owned_attachment(
        self,
        db: AsyncSession,
        thread_id: UUID,
        attachment_id: UUID,
        user_id: UUID,
    ) -> Attachment | None:
        stmt = select(Attachment).where(
            Attachment.id == attachment_id,
            Attachment.user_id == user_id,
            Attachment.thread_id == thread_id,
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def _get_recent_memory(self, db: AsyncSession, thread_id: UUID, user_id: UUID, limit: int = 5) -> list[ChatMessage]:
        stmt = (
            select(ChatMessage)
            .where(
                ChatMessage.thread_id == thread_id,
                ChatMessage.user_id == user_id,
                ChatMessage.role.in_(["user", "assistant"]),
            )
            .order_by(desc(ChatMessage.created_at))
            .limit(max(1, limit) * 2)
        )
        result = await db.execute(stmt)
        messages = result.scalars().all()
        messages.reverse()
        return messages

    @staticmethod
    def _format_memory(messages: list[ChatMessage]) -> str:
        if not messages:
            return ""

        lines: list[str] = []
        for message in messages:
            role = "User" if message.role == "user" else "Assistant"
            lines.append(f"{role}: {message.content}")
        return "\n\n".join(lines)

    @staticmethod
    def _build_context_and_sources(
        documents: list[str],
        metadatas: list[dict] | list,
        distances: list[float] | list,
        attachment_id: UUID,
    ) -> tuple[str, list[dict[str, object]]]:
        context_blocks: list[str] = []
        sources: list[dict[str, object]] = []

        for index, document in enumerate(documents):
            metadata = metadatas[index] if index < len(metadatas) else {}
            distance = distances[index] if index < len(distances) else None
            chunk_index = int(metadata.get("chunk_index", index)) if isinstance(metadata, dict) else index
            excerpt = str(document)[:280]

            context_blocks.append(f"Chunk {chunk_index}:\n{document}")
            sources.append(
                {
                    "attachment_id": attachment_id,
                    "chunk_index": chunk_index,
                    "score": float(distance) if distance is not None else None,
                    "excerpt": excerpt,
                }
            )

        return "\n\n".join(context_blocks), sources

    async def ingest_pdf(
        self,
        db: AsyncSession,
        *,
        thread_id: UUID,
        attachment_id: UUID,
        user_id: UUID,
        attachment_bytes_loader,
    ) -> tuple[Attachment, int]:
        thread = await self._get_owned_thread(db, thread_id, user_id)
        if not thread:
            raise ValueError("Thread not found")

        attachment = await self._get_owned_attachment(db, thread_id, attachment_id, user_id)
        if not attachment:
            raise ValueError("Attachment not found")

        if attachment.attachment_type != "pdf" and attachment.mime_type != "application/pdf":
            raise ValueError("Attachment is not a PDF")

        attachment.indexed_status = "indexing"
        attachment.indexing_error = None
        await db.commit()

        try:
            pdf_bytes = await attachment_bytes_loader(attachment)
            pdf_text = self._extract_pdf_text(pdf_bytes)
            chunks = self._chunk_text(pdf_text)
            if not chunks:
                raise ValueError("No extractable text found in PDF")

            embedding_client = get_litellm_openai_client()
            embedding_response = embedding_client.embeddings.create(
                model=settings.litellm_embedding_model,
                input=chunks,
            )
            embeddings = [item.embedding for item in embedding_response.data]

            collection = self._get_collection(user_id)
            ids = [f"{attachment_id}:{index}" for index in range(len(chunks))]
            metadatas = [
                {
                    "attachment_id": str(attachment_id),
                    "thread_id": str(thread_id),
                    "chunk_index": index,
                    "filename": attachment.original_filename,
                }
                for index in range(len(chunks))
            ]
            collection.upsert(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)

            attachment.indexed_status = "indexed"
            attachment.chunk_count = len(chunks)
            attachment.indexed_at = datetime.now(timezone.utc)
            attachment.indexing_error = None
            await db.commit()
            await db.refresh(attachment)
            return attachment, len(chunks)
        except Exception as exc:
            attachment.indexed_status = "failed"
            attachment.chunk_count = 0
            attachment.indexing_error = str(exc)
            await db.commit()
            raise

    async def ask_pdf(
        self,
        db: AsyncSession,
        *,
        thread_id: UUID,
        attachment_id: UUID,
        user_id: UUID,
        question: str,
    ) -> tuple[str, list[dict[str, object]]]:
        thread = await self._get_owned_thread(db, thread_id, user_id)
        if not thread:
            raise ValueError("Thread not found")

        attachment = await self._get_owned_attachment(db, thread_id, attachment_id, user_id)
        if not attachment:
            raise ValueError("Attachment not found")

        if attachment.indexed_status != "indexed":
            raise ValueError("PDF is not indexed yet")

        embedding_client = get_litellm_openai_client()
        question_embedding = embedding_client.embeddings.create(
            model=settings.litellm_embedding_model,
            input=question,
        )

        query_vector = question_embedding.data[0].embedding
        collection = self._get_collection(user_id)
        query_result = collection.query(
            query_embeddings=[query_vector],
            n_results=6,
            where={"attachment_id": str(attachment_id)},
            include=["documents", "metadatas", "distances"],
        )

        documents = (query_result.get("documents") or [[]])[0]
        metadatas = (query_result.get("metadatas") or [[]])[0]
        distances = (query_result.get("distances") or [[]])[0]

        if not documents:
            raise ValueError("No indexed chunks found for this PDF")

        memory_messages = await self._get_recent_memory(db, thread_id, user_id, limit=5)
        memory_text = self._format_memory(memory_messages)

        context_text, sources = self._build_context_and_sources(documents, metadatas, distances, attachment_id)
        prompt = (
            "You are a document assistant. Use only the provided PDF context and chat memory. "
            "If the answer is not in the context, say you cannot find it in this document.\n\n"
            f"Conversation memory:\n{memory_text or 'None'}\n\n"
            f"PDF context:\n{context_text}\n\n"
            f"Question: {question}"
        )

        completion = embedding_client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": "Answer from the provided PDF context with concise, faithful responses."},
                {"role": "user", "content": prompt},
            ],
        )

        answer = (completion.choices[0].message.content or "").strip()
        if not answer:
            answer = "I could not find a confident answer in the selected PDF."

        await self.thread_service.add_message(db, thread_id, user_id, "user", question)
        await self.thread_service.add_message(db, thread_id, user_id, "assistant", answer)

        return answer, sources
