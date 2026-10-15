from pydantic import BaseModel, Field
from typing import Optional


# ── Response Schemas ─────────────────────────────────────────

class AlertResponse(BaseModel):
    id: str
    target_user_id: str
    patient_id: Optional[str] = None
    patient_name: Optional[str] = None
    alert_type: str
    severity: str
    message: str
    is_read: bool
    created_at: Optional[str] = None


class AlertListResponse(BaseModel):
    alerts: list[AlertResponse]
    total: int
    unread: int


class UnreadCountResponse(BaseModel):
    unread: int


class MarkReadResponse(BaseModel):
    message: str
    updated: int = Field(0, description="Number of alerts marked as read")
