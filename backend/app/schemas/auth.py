from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


ALLOWED_SIGNUP_DOMAINS = {"amzur.com", "stackyon.com"}


class ThreadMessageBase(BaseModel):
    role: str
    content: str


class ThreadMessageResponse(ThreadMessageBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class ChatThreadCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class ChatThreadResponse(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProfileResponse(BaseModel):
    id: UUID
    email: str
    full_name: str | None

    class Config:
        from_attributes = True


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str | None = None

    @field_validator("email")
    @classmethod
    def validate_company_domain(cls, value: EmailStr) -> EmailStr:
        domain = value.split("@", 1)[1].lower()
        if domain not in ALLOWED_SIGNUP_DOMAINS:
            raise ValueError("Signup is allowed only for amzur.com or stackyon.com email addresses")
        return value


class SignInRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleSignInRequest(BaseModel):
    id_token: str = Field(min_length=1)


class AuthResponse(BaseModel):
    access_token: str
    user: ProfileResponse


class MessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10000)
