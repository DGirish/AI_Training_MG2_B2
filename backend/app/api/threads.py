from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import decode_token
from app.db.session import get_db
from app.schemas.thread import ThreadCreate, ThreadResponse, ThreadUpdate
from app.services.auth_service import AuthService
from app.services.thread_service import ThreadService

router = APIRouter(prefix="/api/threads", tags=["threads"])
thread_service = ThreadService()
auth_service = AuthService()


def _db_unavailable_http_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Database unavailable. Check Supabase connectivity and try again.",
    )


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


@router.get("", response_model=list[ThreadResponse])
async def list_threads(token: str | None = None, db: AsyncSession = Depends(get_db)):
    try:
        user_id = _get_current_user_id(token)
        threads = await thread_service.get_user_threads(db, user_id)
        return [ThreadResponse.model_validate(t) for t in threads]
    except HTTPException:
        raise
    except (SQLAlchemyError, OSError):
        raise _db_unavailable_http_error()
    except Exception:
        raise _db_unavailable_http_error()


@router.post("", response_model=ThreadResponse)
async def create_thread(data: ThreadCreate, token: str | None = None, db: AsyncSession = Depends(get_db)):
    try:
        user_id = _get_current_user_id(token)
        thread = await thread_service.create_thread(db, user_id, data)
        return ThreadResponse(
            id=thread.id,
            title=thread.title,
            created_at=thread.created_at,
            updated_at=thread.updated_at,
            messages=[],
        )
    except HTTPException:
        raise
    except (SQLAlchemyError, OSError):
        raise _db_unavailable_http_error()
    except Exception:
        raise _db_unavailable_http_error()


@router.get("/{thread_id}", response_model=ThreadResponse)
async def get_thread(thread_id: UUID, token: str | None = None, db: AsyncSession = Depends(get_db)):
    try:
        user_id = _get_current_user_id(token)
        thread = await thread_service.get_thread_by_id(db, thread_id, user_id)
        if not thread:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
        return ThreadResponse.model_validate(thread)
    except HTTPException:
        raise
    except (SQLAlchemyError, OSError):
        raise _db_unavailable_http_error()
    except Exception:
        raise _db_unavailable_http_error()


@router.delete("/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_thread(thread_id: UUID, token: str | None = None, db: AsyncSession = Depends(get_db)):
    try:
        user_id = _get_current_user_id(token)
        deleted = await thread_service.delete_thread(db, thread_id, user_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    except HTTPException:
        raise
    except (SQLAlchemyError, OSError):
        raise _db_unavailable_http_error()
    except Exception:
        raise _db_unavailable_http_error()


@router.put("/{thread_id}", response_model=ThreadResponse)
async def update_thread(
    thread_id: UUID,
    data: ThreadUpdate,
    token: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    try:
        user_id = _get_current_user_id(token)
        thread = await thread_service.update_thread(db, thread_id, user_id, data)
        if not thread:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
        return ThreadResponse.model_validate(thread)
    except HTTPException:
        raise
    except (SQLAlchemyError, OSError):
        raise _db_unavailable_http_error()
    except Exception:
        raise _db_unavailable_http_error()
