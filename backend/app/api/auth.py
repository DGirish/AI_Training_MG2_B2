from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import create_access_token, decode_token
from app.core.config import settings
from app.core.db_diagnostics import db_unavailable_http_error
from app.db.session import get_db
from app.schemas.auth import (
    AuthResponse,
    GoogleSignInRequest,
    ProfileResponse,
    SignInRequest,
    SignUpRequest,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])
auth_service = AuthService()


@router.post("/signup", response_model=AuthResponse)
async def signup(data: SignUpRequest, db: Annotated[AsyncSession, Depends(get_db)] = ...) -> AuthResponse:
    try:
        user_id = uuid4()
        profile = await auth_service.sign_up(db, data, user_id)

        token_data = {"sub": str(profile.id), "email": profile.email}
        access_token = create_access_token(token_data)

        return AuthResponse(
            access_token=access_token,
            user=ProfileResponse.model_validate(profile),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except (SQLAlchemyError, OSError) as exc:
        raise db_unavailable_http_error(
            "auth.signup",
            exc,
            "Database unavailable. Check database connectivity and try again.",
        )
    except Exception as exc:
        raise db_unavailable_http_error(
            "auth.signup.unexpected",
            exc,
            "Database unavailable. Check database connectivity and try again.",
        )


@router.post("/signin", response_model=AuthResponse)
async def signin(data: SignInRequest, db: Annotated[AsyncSession, Depends(get_db)] = ...) -> AuthResponse:
    try:
        profile = await auth_service.authenticate(db, data.email, data.password)
        if not profile:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        token_data = {"sub": str(profile.id), "email": profile.email}
        access_token = create_access_token(token_data)

        return AuthResponse(
            access_token=access_token,
            user=ProfileResponse.model_validate(profile),
        )
    except HTTPException:
        raise
    except (SQLAlchemyError, OSError) as exc:
        raise db_unavailable_http_error(
            "auth.signin",
            exc,
            "Database unavailable. Check database connectivity and try again.",
        )
    except Exception as exc:
        raise db_unavailable_http_error(
            "auth.signin.unexpected",
            exc,
            "Database unavailable. Check database connectivity and try again.",
        )


@router.get("/google/client-id")
async def google_client_id() -> dict[str, str | None]:
    return {"client_id": settings.google_client_id}


@router.post("/google/signin", response_model=AuthResponse)
async def google_signin(data: GoogleSignInRequest, db: Annotated[AsyncSession, Depends(get_db)] = ...) -> AuthResponse:
    try:
        profile = await auth_service.sign_in_with_google(db, data.id_token)

        token_data = {"sub": str(profile.id), "email": profile.email}
        access_token = create_access_token(token_data)

        return AuthResponse(
            access_token=access_token,
            user=ProfileResponse.model_validate(profile),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except HTTPException:
        raise
    except (SQLAlchemyError, OSError) as exc:
        raise db_unavailable_http_error(
            "auth.google_signin",
            exc,
            "Database unavailable. Check database connectivity and try again.",
        )
    except Exception as exc:
        raise db_unavailable_http_error(
            "auth.google_signin.unexpected",
            exc,
            "Database unavailable. Check database connectivity and try again.",
        )


@router.get("/me", response_model=ProfileResponse)
async def get_current_user(token: str | None = None, db: AsyncSession = Depends(get_db)) -> ProfileResponse:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No token provided")

    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing user ID")

    try:
        from uuid import UUID

        user_id = UUID(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user ID in token")

    profile = await auth_service.get_profile_by_id(db, user_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return ProfileResponse.model_validate(profile)
