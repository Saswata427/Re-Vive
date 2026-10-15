from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


# ── Enums ────────────────────────────────────────────────────

class MoodLevel(str, Enum):
    GOOD = "good"
    NEUTRAL = "neutral"
    POOR = "poor"


# ── Request Schemas ──────────────────────────────────────────

class CheckinCreate(BaseModel):
    """Daily behavioural recovery check-in."""
    mood: MoodLevel = Field(..., description="Overall mood today")
    stress_level: int = Field(..., ge=1, le=10, description="Stress on a scale of 1-10")
    sleep_hours: float = Field(..., ge=0, le=24, description="Hours of sleep last night")
    craving_level: int = Field(..., ge=1, le=10, description="Craving intensity 1-10")
    medication_taken: bool = Field(..., description="Whether all prescribed meds were taken")
    physical_activity_minutes: int = Field(
        0, ge=0, le=600, description="Minutes of physical activity today"
    )
    notes: Optional[str] = Field(None, max_length=2000, description="Optional free-text notes")


# ── Response Schemas ─────────────────────────────────────────

class CheckinResponse(BaseModel):
    id: str
    patient_id: str
    date: str
    mood: str
    stress_level: int
    sleep_hours: float
    craving_level: int
    medication_taken: bool
    physical_activity_minutes: int = 0
    notes: Optional[str] = None
    created_at: Optional[str] = None


class CheckinListResponse(BaseModel):
    checkins: list[CheckinResponse]
    total: int


class CareTeamMember(BaseModel):
    id: str
    full_name: str
    role: str
    email: Optional[str] = None
    phone: Optional[str] = None


class RecoveryGoalSummary(BaseModel):
    id: str
    title: str
    status: str
    target_date: Optional[str] = None


class PatientDashboardResponse(BaseModel):
    full_name: str
    today_checkin_done: bool
    streak_days: int
    abstinence_days: Optional[int] = None
    sobriety_date: Optional[str] = None
    active_goals: int
    total_goals: int
    care_team: list[CareTeamMember] = []
    recent_goals: list[RecoveryGoalSummary] = []


class PatientProfileResponse(BaseModel):
    id: str
    full_name: str
    email: str
    phone: Optional[str] = None
    primary_condition: Optional[str] = None
    program_start_date: Optional[str] = None
    sobriety_date: Optional[str] = None
    therapy_program: Optional[str] = None
    emergency_contact: Optional[str] = None
    medical_notes: Optional[str] = None
    abstinence_days: Optional[int] = None
    assigned_doctor: Optional[CareTeamMember] = None
    guardian: Optional[CareTeamMember] = None
    created_at: Optional[str] = None


class GoalListResponse(BaseModel):
    goals: list[RecoveryGoalSummary]
    total: int
