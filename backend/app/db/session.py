from __future__ import annotations

import asyncio
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


if not settings.database_url:
    raise RuntimeError("DATABASE_URL is required and must point to Supabase.")

engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_use_lifo=True,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout_seconds,
    pool_recycle=settings.db_pool_recycle_seconds,
    connect_args={
        "timeout": settings.db_connect_timeout_seconds,
        "command_timeout": settings.db_command_timeout_seconds,
    },
)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        max_attempts = max(settings.db_connect_retries, 1)
        last_exc: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                await session.execute(text("SELECT 1"))
                break
            except (SQLAlchemyError, OSError) as exc:
                last_exc = exc
                if attempt >= max_attempts:
                    raise
                await session.rollback()
                await asyncio.sleep(settings.db_connect_retry_backoff_seconds * attempt)

        if last_exc and max_attempts == 1:
            raise last_exc

        try:
            yield session
        finally:
            await session.close()
