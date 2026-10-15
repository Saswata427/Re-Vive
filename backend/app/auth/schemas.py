from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    HOSPITAL = "hospital"
    DOCTOR = "doctor"
    PATIENT = "patient"
    GUARDIAN = "guardian"


# ── Request Schemas ──────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)
    device_label: Optional[str] = Field(
        None,
        max_length=100,
        description="Optional client label (e.g. \"Pixel 8\") so a user can tell "
                    "their sessions apart when revoking one.",
    )


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = Field(
        None,
        description="Revoke just this session. Omit to sign out everywhere.",
    )


# ── Response Schemas ─────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: str
    full_name: str
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = Field(
        None, description="Access token lifetime in seconds."
    )


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    phone: Optional[str] = None
    role: str
    is_active: bool
    hospital_id: Optional[str] = None
    created_at: Optional[str] = None


class MessageResponse(BaseModel):
    message: str
