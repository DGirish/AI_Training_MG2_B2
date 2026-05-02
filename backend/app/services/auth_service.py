from __future__ import annotations

import asyncio
import logging
from uuid import UUID, uuid4

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password, verify_password
from app.core.config import settings
from app.models.models import Profile
from app.schemas.auth import ALLOWED_SIGNUP_DOMAINS, SignUpRequest

logger = logging.getLogger(__name__)


class AuthService:
    async def sign_up(self, db: AsyncSession, signup_data: SignUpRequest, user_id: UUID) -> Profile:
        existing = await db.execute(select(Profile).where(Profile.email == signup_data.email))
        if existing.scalars().first():
            raise ValueError("Email already registered")

        profile = Profile(
            id=user_id,
            email=signup_data.email,
            password_hash=hash_password(signup_data.password),
            full_name=signup_data.full_name,
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
        return profile

    async def authenticate(self, db: AsyncSession, email: str, password: str) -> Profile | None:
        profile = await self.get_profile_by_email(db, email)
        if not profile or not profile.password_hash:
            return None

        try:
            if not verify_password(password, profile.password_hash):
                return None
        except ValueError:
            return None

        return profile

    async def sign_in_with_google(self, db: AsyncSession, id_token: str) -> Profile:
        if not settings.google_client_id:
            raise ValueError("Google login is not configured")

        try:
            def _verify_token() -> dict:
                return google_id_token.verify_oauth2_token(
                    id_token,
                    google_requests.Request(),
                    settings.google_client_id,
                    clock_skew_in_seconds=60,
                )

            loop = asyncio.get_event_loop()
            payload = await loop.run_in_executor(None, _verify_token)
        except Exception as exc:
            logger.error("Google token verification failed: %s: %s", type(exc).__name__, exc)
            # Try without audience check to give a better diagnostic error
            try:
                def _decode_no_audience() -> dict:
                    return google_id_token.verify_oauth2_token(
                        id_token,
                        google_requests.Request(),
                        audience=None,
                        clock_skew_in_seconds=60,
                    )
                diag_payload = await loop.run_in_executor(None, _decode_no_audience)
                token_aud = diag_payload.get("aud", "unknown")
                raise ValueError(
                    f"Google token audience mismatch: token was issued for '{token_aud}', "
                    f"expected '{settings.google_client_id}'. "
                    "Ensure the correct OAuth Client ID is used in both GCP Console and .env."
                ) from exc
            except ValueError:
                raise
            except Exception:
                raise ValueError(f"Invalid Google token: {exc}") from exc

        email = (payload.get("email") or "").strip().lower()
        email_verified = bool(payload.get("email_verified"))
        if not email or not email_verified:
            raise ValueError("Google account email is not verified")

        domain = email.split("@", 1)[1] if "@" in email else ""
        if domain not in ALLOWED_SIGNUP_DOMAINS:
            raise ValueError("Login is allowed only for amzur.com or stackyon.com email addresses")

        profile = await self.get_profile_by_email(db, email)
        if profile:
            return profile

        full_name = payload.get("name") or payload.get("given_name")
        new_id = uuid4()

        # Use INSERT ... ON CONFLICT DO NOTHING to prevent race-condition duplicates.
        # If another request (or stale pooler session) already inserted the row,
        # we just re-fetch below.
        await db.execute(
            text(
                """
                INSERT INTO profiles (id, email, password_hash, full_name)
                VALUES (:id, :email, NULL, :full_name)
                ON CONFLICT (email) DO NOTHING
                """
            ),
            {"id": str(new_id), "email": email, "full_name": full_name},
        )
        await db.commit()

        # Always re-fetch so we return the canonical row (whether new or pre-existing).
        profile = await self.get_profile_by_email(db, email)
        if profile is None:
            raise RuntimeError(f"Failed to create or retrieve profile for {email}")
        return profile

    async def get_profile_by_email(self, db: AsyncSession, email: str) -> Profile | None:
        result = await db.execute(select(Profile).where(Profile.email == email))
        return result.scalars().first()

    async def get_profile_by_id(self, db: AsyncSession, user_id: UUID) -> Profile | None:
        result = await db.execute(select(Profile).where(Profile.id == user_id))
        return result.scalars().first()
