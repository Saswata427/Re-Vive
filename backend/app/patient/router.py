from fastapi import APIRouter, Depends, Request, Query
from typing import Annotated

from app.auth.schemas import UserRole
from app.auth.dependencies import role_required
from app.patient import schemas, service
from app.clinical import schemas as clinical_schemas
from app.common import recovery
from app.common.audit import log_action
from app.common.models import to_object_id

router = APIRouter(prefix="/patient", tags=["Patient"])


def _get_patient_id(user: dict) -> str:
    """Extract the patient's user ID."""
    return user.get("id")


# ── Dashboard ────────────────────────────────────────────────

@router.get("/dashboard", response_model=schemas.PatientDashboardResponse)
async def get_dashboard(
    current_user: Annotated[dict, Depends(role_required(UserRole.PATIENT))]
):
    """Get patient-specific dashboard: check-in status, streak, goals, care team."""
    patient_id = _get_patient_id(current_user)
    return await service.get_patient_dashboard(patient_id)


# ── Daily Check-in ───────────────────────────────────────────

@router.post("/checkin", response_model=schemas.CheckinResponse, status_code=201)
async def submit_checkin(
    body: schemas.CheckinCreate,
    request: Request,
    current_user: Annotated[dict, Depends(role_required(UserRole.PATIENT))],
):
    """Submit today's daily wellness check-in."""
    patient_id = _get_patient_id(current_user)
    checkin = await service.submit_checkin(patient_id, body.model_dump())

    await log_action(
        user_id=patient_id,
        action="submitted_daily_checkin",
        resource_type="daily_checkin",
        resource_id=checkin["id"],
        details={
            "mood": body.mood.value,
            "craving_level": body.craving_level,
            "stress_level": body.stress_level,
        },
        ip_address=request.client.host if request.client else None,
    )

    return checkin


# ── Check-in History ─────────────────────────────────────────

@router.get("/checkins", response_model=schemas.CheckinListResponse)
async def list_checkins(
    current_user: Annotated[dict, Depends(role_required(UserRole.PATIENT))],
    limit: int = Query(30, ge=1, le=100),
):
    """Get the patient's historical check-in logs."""
    patient_id = _get_patient_id(current_user)
    checkins = await service.get_checkin_history(patient_id, limit)
    return schemas.CheckinListResponse(checkins=checkins, total=len(checkins))


# ── Recovery Goals ───────────────────────────────────────────

@router.get("/goals", response_model=schemas.GoalListResponse)
async def list_goals(
    current_user: Annotated[dict, Depends(role_required(UserRole.PATIENT))],
):
    """Get the patient's assigned recovery goals."""
    patient_id = _get_patient_id(current_user)
    goals = await service.get_patient_goals(patient_id)
    return schemas.GoalListResponse(goals=goals, total=len(goals))


# ── Recovery Score ───────────────────────────────────────────

@router.get("/recovery-score", response_model=clinical_schemas.RecoveryScoreResponse)
async def get_recovery_score(
    current_user: Annotated[dict, Depends(role_required(UserRole.PATIENT))],
    window_days: int = Query(30, ge=7, le=90),
):
    """Get the patient's own recovery score and component breakdown."""
    patient_id = _get_patient_id(current_user)
    return await recovery.calculate_recovery_score(to_object_id(patient_id), window_days)


# ── Digital Twin ─────────────────────────────────────────────

@router.get("/digital-twin", response_model=clinical_schemas.DigitalTwinResponse)
async def get_digital_twin(
    current_user: Annotated[dict, Depends(role_required(UserRole.PATIENT))],
    window_days: int = Query(30, ge=7, le=90),
    horizon_days: int = Query(30, ge=7, le=90),
):
    """The patient's own digital twin — current recovery state and what-if projections."""
    patient_id = _get_patient_id(current_user)
    return await recovery.build_digital_twin(
        to_object_id(patient_id), window_days, horizon_days
    )


# ── Patient Profile ──────────────────────────────────────────

@router.get("/profile", response_model=schemas.PatientProfileResponse)
async def get_profile(
    current_user: Annotated[dict, Depends(role_required(UserRole.PATIENT))],
):
    """Get the patient's medical profile and care team contacts."""
    patient_id = _get_patient_id(current_user)
    return await service.get_patient_profile(patient_id)
