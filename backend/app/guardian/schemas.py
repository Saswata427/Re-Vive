from pydantic import BaseModel
from typing import Optional


# ── Response Schemas ─────────────────────────────────────────

class CareTeamMember(BaseModel):
    id: str
    full_name: str
    role: str
    email: Optional[str] = None
    phone: Optional[str] = None


class CheckinSummary(BaseModel):
    id: str
    date: str
    mood: Optional[str] = None
    stress_level: Optional[int] = None
    sleep_hours: Optional[float] = None
    craving_level: Optional[int] = None
    medication_taken: Optional[bool] = None
    physical_activity_minutes: Optional[int] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None


class RecoveryGoalSummary(BaseModel):
    id: str
    title: str
    status: str
    target_date: Optional[str] = None


class GuardianDashboardResponse(BaseModel):
    recovery_score: Optional[int] = None
    recovery_band: Optional[str] = None
    recovery_label: Optional[str] = None
    recovery_trend: Optional[str] = None
    guardian_name: str
    patient_name: str
    patient_id: str
    primary_condition: Optional[str] = None
    today_checkin_done: bool
    latest_craving_level: Optional[int] = None
    latest_stress_level: Optional[int] = None
    latest_mood: Optional[str] = None
    streak_days: int
    abstinence_days: Optional[int] = None
    sobriety_date: Optional[str] = None
    active_goals: int
    total_goals: int
    unread_alerts: int
    care_team: list[CareTeamMember] = []


class PatientOverviewResponse(BaseModel):
    patient_id: str
    patient_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    primary_condition: Optional[str] = None
    program_start_date: Optional[str] = None
    sobriety_date: Optional[str] = None
    therapy_program: Optional[str] = None
    medical_notes: Optional[str] = None
    abstinence_days: Optional[int] = None
    recent_checkins: list[CheckinSummary] = []
    goals: list[RecoveryGoalSummary] = []
    care_team: list[CareTeamMember] = []
