from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import ChatMessage, ChatThread
from app.schemas.thread import ThreadCreate, ThreadUpdate
from app.services.thread_naming_service import ThreadNamingService


DEFAULT_THREAD_TITLES = {"new chat", "new thread", "untitled"}


class ThreadService:
    def __init__(self) -> None:
        self.thread_naming_service = ThreadNamingService()

    async def get_user_threads(self, db: AsyncSession, user_id: UUID) -> list[ChatThread]:
        stmt = (
            select(ChatThread)
            .where(ChatThread.user_id == user_id)
            .order_by(desc(ChatThread.updated_at))
            .options(selectinload(ChatThread.messages))
        )
        result = await db.execute(stmt)
        return result.scalars().unique().all()

    async def get_thread_by_id(self, db: AsyncSession, thread_id: UUID, user_id: UUID) -> ChatThread | None:
        stmt = (
            select(ChatThread)
            .where(and_(ChatThread.id == thread_id, ChatThread.user_id == user_id))
            .options(selectinload(ChatThread.messages))
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def create_thread(self, db: AsyncSession, user_id: UUID, data: ThreadCreate) -> ChatThread:
        thread = ChatThread(user_id=user_id, title=data.title)
        db.add(thread)
        await db.commit()
        await db.refresh(thread)
        return thread

    async def update_thread(self, db: AsyncSession, thread_id: UUID, user_id: UUID, data: ThreadUpdate) -> ChatThread | None:
        thread = await self.get_thread_by_id(db, thread_id, user_id)
        if not thread:
            return None

        thread.title = data.title.strip()
        await db.commit()
        await db.refresh(thread)
        return thread

    async def delete_thread(self, db: AsyncSession, thread_id: UUID, user_id: UUID) -> bool:
        result = await db.execute(
            select(ChatThread).where(and_(ChatThread.id == thread_id, ChatThread.user_id == user_id))
        )
        thread = result.scalars().first()
        if thread:
            await db.delete(thread)
            await db.commit()
            return True
        return False

    async def add_message(
        self, db: AsyncSession, thread_id: UUID, user_id: UUID, role: str, content: str
    ) -> ChatMessage:
        message = ChatMessage(thread_id=thread_id, user_id=user_id, role=role, content=content)
        db.add(message)
        await db.commit()
        await db.refresh(message)
        return message

    async def maybe_name_thread_from_first_user_message(
        self,
        db: AsyncSession,
        thread_id: UUID,
        user_id: UUID,
        first_message: str,
    ) -> None:
        thread = await self.get_thread_by_id(db, thread_id, user_id)
        if not thread:
            return

        if thread.title.strip().lower() not in DEFAULT_THREAD_TITLES:
            return

        user_message_count_stmt = select(func.count(ChatMessage.id)).where(
            ChatMessage.thread_id == thread_id,
            ChatMessage.role == "user",
        )
        result = await db.execute(user_message_count_stmt)
        user_message_count = result.scalar_one()

        if user_message_count != 1:
            return

        generated_title = await self.thread_naming_service.generate_title(first_message)
        thread.title = generated_title
        await db.commit()
