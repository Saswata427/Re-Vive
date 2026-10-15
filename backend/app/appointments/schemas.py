from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


# ── Enums ────────────────────────────────────────────────────

class AppointmentStatus(str, Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# ── Request Schemas ──────────────────────────────────────────

class AppointmentCreate(BaseModel):
    patient_id: str = Field(..., description="ID of the patient to schedule")
    date_time: datetime = Field(..., description="Appointment start time (ISO 8601)")
    duration_minutes: int = Field(30, ge=5, le=480, description="Length in minutes")
    reason: str = Field(..., min_length=1, max_length=200, description="Visit reason")
    notes: Optional[str] = Field(None, max_length=2000)


class AppointmentUpdate(BaseModel):
    date_time: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, ge=5, le=480)
    reason: Optional[str] = Field(None, min_length=1, max_length=200)
    status: Optional[AppointmentStatus] = None
    notes: Optional[str] = Field(None, max_length=2000)


# ── Response Schemas ─────────────────────────────────────────

class AppointmentResponse(BaseModel):
    id: str
    patient_id: str
    patient_name: Optional[str] = None
    doctor_id: str
    doctor_name: Optional[str] = None
    hospital_id: Optional[str] = None
    date_time: str
    duration_minutes: int = 30
    reason: str
    status: str
    notes: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AppointmentListResponse(BaseModel):
    appointments: list[AppointmentResponse]
    total: int
    upcoming: int
