from pydantic import BaseModel, Field
from typing import Optional


# ── Request Schemas ──────────────────────────────────────────

class DeviceRegisterRequest(BaseModel):
    token: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Expo push token, e.g. ExponentPushToken[xxxxxxxx].",
    )
    platform: Optional[str] = Field(
        None, max_length=20, description="ios | android | web"
    )
    device_label: Optional[str] = Field(
        None, max_length=100, description="Human-readable device name."
    )
    app_version: Optional[str] = Field(None, max_length=30)


# ── Response Schemas ─────────────────────────────────────────

class DeviceResponse(BaseModel):
    id: str
    token: str
    platform: Optional[str] = None
    device_label: Optional[str] = None
    app_version: Optional[str] = None
    created_at: Optional[str] = None
    last_seen_at: Optional[str] = None


class DeviceListResponse(BaseModel):
    devices: list[DeviceResponse]
    total: int


class MessageResponse(BaseModel):
    message: str
