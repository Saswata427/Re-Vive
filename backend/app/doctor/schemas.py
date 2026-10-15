from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


# ── Enums ────────────────────────────────────────────────────

class NoteType(str, Enum):
    PROGRESS = "progress"
    OBSERVATION = "observation"
    CONCERN = "concern"


class GoalStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


# ── Response Schemas ─────────────────────────────────────────

class DoctorDashboardStats(BaseModel):
    assigned_patients: int
    recent_checkins: int  # check-ins in last 7 days
    active_goals: int
    total_notes: int


class PatientSummary(BaseModel):
    id: str
    full_name: str
    email: str
    phone: Optional[str] = None
    is_active: bool
    last_checkin_date: Optional[str] = None
    active_goals: int = 0


class PatientListResponse(BaseModel):
    patients: list[PatientSummary]
    total: int


class PatientDetail(BaseModel):
    id: str
    full_name: str
    email: str
    phone: Optional[str] = None
    is_active: bool
    created_at: Optional[str] = None
    # Clinical profile
    primary_condition: Optional[str] = None
    program_start_date: Optional[str] = None
    sobriety_date: Optional[str] = None
    therapy_program: Optional[str] = None
    emergency_contact: Optional[str] = None
    medical_notes: Optional[str] = None
    abstinence_days: Optional[int] = None
    # Counts
    total_checkins: int = 0
    total_notes: int = 0
    total_goals: int = 0


class PatientProfileUpsert(BaseModel):
    """Fields a doctor or hospital admin may set on a patient's clinical profile."""
    primary_condition: Optional[str] = Field(None, max_length=300)
    program_start_date: Optional[str] = Field(None, description="YYYY-MM-DD")
    sobriety_date: Optional[str] = Field(None, description="YYYY-MM-DD, drives abstinence count")
    therapy_program: Optional[str] = Field(None, max_length=300)
    emergency_contact: Optional[str] = Field(None, max_length=200)
    medical_notes: Optional[str] = Field(None, max_length=5000)


class PatientProfileResponse(BaseModel):
    primary_condition: Optional[str] = None
    program_start_date: Optional[str] = None
    sobriety_date: Optional[str] = None
    therapy_program: Optional[str] = None
    emergency_contact: Optional[str] = None
    medical_notes: Optional[str] = None
    abstinence_days: Optional[int] = None


class CheckinResponse(BaseModel):
    id: str
    patient_id: str
    date: str
    mood: Optional[str] = None
    stress_level: Optional[int] = None
    sleep_hours: Optional[float] = None
    craving_level: Optional[int] = None
    medication_taken: Optional[bool] = None
    physical_activity_minutes: Optional[int] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None


class CheckinListResponse(BaseModel):
    checkins: list[CheckinResponse]
    total: int


# ── Request Schemas ──────────────────────────────────────────

class ClinicalNoteCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    note_type: NoteType = NoteType.PROGRESS


class ClinicalNoteResponse(BaseModel):
    id: str
    patient_id: str
    doctor_id: str
    doctor_name: str
    content: str
    note_type: str
    created_at: Optional[str] = None


class ClinicalNoteListResponse(BaseModel):
    notes: list[ClinicalNoteResponse]
    total: int


class RecoveryGoalCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    target_date: Optional[str] = None


class RecoveryGoalUpdate(BaseModel):
    status: Optional[GoalStatus] = None
    notes: Optional[str] = Field(None, max_length=1000)


class RecoveryGoalResponse(BaseModel):
    id: str
    patient_id: str
    doctor_id: str
    title: str
    description: Optional[str] = None
    status: str
    target_date: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class RecoveryGoalListResponse(BaseModel):
    goals: list[RecoveryGoalResponse]
    total: int


# ── Caseload Analytics ───────────────────────────────────────

class CaseloadPatientRow(BaseModel):
    patient_id: str
    full_name: str
    score: Optional[int] = None
    band: Optional[str] = None
    trend: Optional[str] = None
    abstinence_days: Optional[int] = None
    unread_alerts: int = 0
    last_checkin_date: Optional[str] = None
    weakest_area: Optional[str] = None


class CaseloadAnalyticsResponse(BaseModel):
    total_patients: int = 0
    scored_patients: int = 0
    average_score: Optional[int] = None
    band_counts: dict[str, int] = {}
    needs_attention: list[CaseloadPatientRow] = []
    unread_alerts: int = 0
    pending_outcomes: int = 0
    checkins_last_7_days: int = 0
    engagement_rate: Optional[int] = Field(
        None, description="Percent of expected check-ins received over 7 days"
    )
