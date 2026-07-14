from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., max_length=128)
    captcha_token: str | None = None
    captcha_code: str | None = None
    tenant_code: str | None = None  # 多租户环境下指定租户编码，单租户可留空


class CaptchaResponse(BaseModel):
    token: str
    svg: str


class RegisterRequest(BaseModel):
    username: str | None = None
    password: str = Field(..., min_length=6, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    captcha_token: str | None = None
    captcha_code: str | None = None
    tenant_code: str | None = Field(None, min_length=2, max_length=50, pattern=r'^[a-zA-Z0-9_\-]+$')


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    theme_prefs: Optional[dict] = None
    username: Optional[str] = None
    display_name: Optional[str] = None


class RefreshRequest(BaseModel):
    refresh_token: str


class ProfileResponse(BaseModel):
    id: str
    username: str
    display_name: str
    avatar: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    dept_id: Optional[str] = None
    dept_name: Optional[str] = None
    roles: list[str] = []
    permissions: list[str] = []
    theme_prefs: Optional[dict] = None


class ProfileUpdateRequest(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    avatar: Optional[str] = None
    theme_prefs: Optional[dict] = None

    @field_validator("email", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: str | None) -> str | None:
        if v == "":
            return None
        return v


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6, max_length=128)
