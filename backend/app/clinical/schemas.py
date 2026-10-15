from pydantic import BaseModel, Field
from typing import Optional, Any
from enum import Enum


# ── Enums ────────────────────────────────────────────────────

class InterventionType(str, Enum):
    CHECK_IN_CALL = "check_in_call"
    COUNSELLING_SESSION = "counselling_session"
    THERAPY_REFERRAL = "therapy_referral"
    MEDICATION_CHANGE = "medication_change"
    CARE_PLAN_UPDATE = "care_plan_update"
    ESCALATION = "escalation"
    OTHER = "other"


class OutcomeStatus(str, Enum):
    PENDING = "pending"
    IMPROVED = "improved"
    NO_CHANGE = "no_change"
    WORSENED = "worsened"


# ── Medications ──────────────────────────────────────────────

class MedicationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    dosage: str = Field(..., min_length=1, max_length=100, description="e.g. 50mg")
    frequency: str = Field(..., min_length=1, max_length=100, description="e.g. Twice daily")
    start_date: Optional[str] = Field(None, description="YYYY-MM-DD")
    end_date: Optional[str] = Field(None, description="YYYY-MM-DD")
    notes: Optional[str] = Field(None, max_length=1000)


class MedicationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    dosage: Optional[str] = Field(None, min_length=1, max_length=100)
    frequency: Optional[str] = Field(None, min_length=1, max_length=100)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None


class MedicationResponse(BaseModel):
    id: str
    patient_id: str
    doctor_id: Optional[str] = None
    doctor_name: Optional[str] = None
    name: str
    dosage: str
    frequency: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class MedicationListResponse(BaseModel):
    medications: list[MedicationResponse]
    total: int
    active: int


# ── Vitals ───────────────────────────────────────────────────

class VitalsCreate(BaseModel):
    blood_pressure: Optional[str] = Field(None, max_length=20, description="e.g. 120/80")
    heart_rate: Optional[int] = Field(None, ge=20, le=250, description="bpm")
    temperature: Optional[float] = Field(None, ge=25, le=45, description="degrees Celsius")
    weight: Optional[float] = Field(None, ge=1, le=500, description="kilograms")
    notes: Optional[str] = Field(None, max_length=1000)


class VitalsResponse(BaseModel):
    id: str
    patient_id: str
    recorded_by: Optional[str] = None
    recorded_by_name: Optional[str] = None
    recorded_at: Optional[str] = None
    blood_pressure: Optional[str] = None
    heart_rate: Optional[int] = None
    temperature: Optional[float] = None
    weight: Optional[float] = None
    notes: Optional[str] = None


class VitalsListResponse(BaseModel):
    vitals: list[VitalsResponse]
    total: int


# ── Aggregated Medical History ───────────────────────────────

class HistoryEvent(BaseModel):
    event_type: str = Field(..., description="checkin | note | goal | medication | vitals | appointment")
    occurred_at: str
    title: str
    summary: Optional[str] = None
    detail: dict[str, Any] = {}


class MedicalHistoryResponse(BaseModel):
    patient_id: str
    patient_name: str
    profile: dict[str, Any] = {}
    events: list[HistoryEvent] = []
    total: int


# ── Recovery Score ───────────────────────────────────────────

class ScoreComponent(BaseModel):
    key: str
    label: str
    subscore: int = Field(..., description="0-100 for this component alone")
    weight: int = Field(..., description="Percentage this component contributes")
    contribution: float = Field(..., description="Points this component adds to the total")
    detail: str = Field(..., description="Plain-language explanation")


class RecoveryScoreResponse(BaseModel):
    score: Optional[int] = Field(None, description="0-100; null when there is too little data")
    band: Optional[str] = Field(None, description="strong | steady | fragile | at_risk")
    label: str
    trend: Optional[str] = Field(None, description="improving | stable | declining")
    checkins_counted: int = 0
    window_days: int = 30
    abstinence_days: Optional[int] = None
    components: list[ScoreComponent] = []
    explanation: str


# ── Recovery Timeline ────────────────────────────────────────

class TimelineEntry(BaseModel):
    date: str
    daily_score: Optional[int] = None
    events: list[HistoryEvent] = []
    event_count: int = 0


class RecoveryTimelineResponse(BaseModel):
    patient_id: str
    patient_name: str
    days: int
    entries: list[TimelineEntry] = []
    total_events: int = 0


# ── Digital Twin ─────────────────────────────────────────────

class TwinProjectionPoint(BaseModel):
    day: int = Field(..., description="Days from now")
    score: int = Field(..., description="Projected 0-100 score at that day")


class TwinScenario(BaseModel):
    key: str
    label: str = Field(..., description="Plain-language description of the change")
    rationale: str
    component: str = Field(..., description="Score component this scenario moves")
    component_label: str
    baseline_subscore: int
    projected_subscore: int
    score_delta: float = Field(..., description="Points added to the headline score")
    projected_score: int
    projected_band: str
    projected_label: str
    projection: list[TwinProjectionPoint] = []


class TwinCombined(BaseModel):
    label: str
    projected_score: int
    score_delta: float
    projected_band: str
    projected_label: str
    projection: list[TwinProjectionPoint] = []


class DigitalTwinResponse(BaseModel):
    patient_id: str
    window_days: int
    horizon_days: int
    generated_at: str
    disclaimer: str = Field(..., description="Prototype caveat — always present")
    available: bool = Field(..., description="False when the score itself has too little data")
    reason: Optional[str] = Field(None, description="Why the twin is unavailable, when it is")
    baseline: RecoveryScoreResponse
    baseline_projection: list[TwinProjectionPoint] = Field(
        default_factory=list, description="Where the score heads if nothing changes"
    )
    baseline_slope_per_week: float = 0.0
    scenarios: list[TwinScenario] = []
    combined: Optional[TwinCombined] = None


# ── Interventions ────────────────────────────────────────────

class InterventionCreate(BaseModel):
    intervention_type: InterventionType = Field(..., description="What kind of action was taken")
    description: str = Field(..., min_length=1, max_length=3000, description="What the doctor did")
    alert_id: Optional[str] = Field(
        None, description="Alert that prompted this; marks it read when linked"
    )
    follow_up_date: Optional[str] = Field(None, description="YYYY-MM-DD")


class InterventionUpdate(BaseModel):
    description: Optional[str] = Field(None, min_length=1, max_length=3000)
    outcome: Optional[str] = Field(None, max_length=3000, description="What resulted")
    outcome_status: Optional[OutcomeStatus] = None
    follow_up_date: Optional[str] = None


class InterventionResponse(BaseModel):
    id: str
    patient_id: str
    doctor_id: str
    doctor_name: Optional[str] = None
    intervention_type: str
    description: str
    alert_id: Optional[str] = None
    alert_summary: Optional[str] = Field(None, description="Message of the linked alert")
    outcome: Optional[str] = None
    outcome_status: str = "pending"
    follow_up_date: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class InterventionListResponse(BaseModel):
    interventions: list[InterventionResponse]
    total: int
    pending_outcomes: int = Field(0, description="Interventions still awaiting an outcome")


# ── Treatment Plan ───────────────────────────────────────────

class TreatmentPlanUpsert(BaseModel):
    summary: str = Field(..., min_length=1, max_length=5000, description="The plan narrative")
    focus_areas: list[str] = Field(
        default_factory=list, description="e.g. craving management, sleep hygiene"
    )
    review_date: Optional[str] = Field(None, description="YYYY-MM-DD, when to revisit")


class TreatmentPlanResponse(BaseModel):
    id: str
    patient_id: str
    doctor_id: str
    doctor_name: Optional[str] = None
    summary: str
    focus_areas: list[str] = []
    review_date: Optional[str] = None
    version: int = 1
    is_current: bool = True
    created_at: Optional[str] = None
    superseded_at: Optional[str] = None


class TreatmentPlanHistoryResponse(BaseModel):
    current: Optional[TreatmentPlanResponse] = None
    history: list[TreatmentPlanResponse] = []
    total_versions: int = 0
