from fastapi import APIRouter, Depends, Request, Query
from typing import Annotated

from app.auth.schemas import UserRole
from app.auth.dependencies import role_required
from app.doctor import schemas, service
from app.clinical import schemas as clinical_schemas
from app.common.audit import log_action

router = APIRouter(prefix="/doctor", tags=["Doctor"])


def _get_doctor_id(user: dict) -> str:
    """Extract the doctor's user ID."""
    return user.get("id")


# ── Dashboard ────────────────────────────────────────────────

@router.get("/dashboard", response_model=schemas.DoctorDashboardStats)
async def get_dashboard(
    current_user: Annotated[dict, Depends(role_required(UserRole.DOCTOR))]
):
    """Get doctor-specific dashboard statistics."""
    doctor_id = _get_doctor_id(current_user)
    return await service.get_doctor_dashboard_stats(doctor_id)


# ── Caseload Analytics ───────────────────────────────────────

@router.get("/analytics", response_model=schemas.CaseloadAnalyticsResponse)
async def get_caseload_analytics(
    current_user: Annotated[dict, Depends(role_required(UserRole.DOCTOR))]
):
    """Cross-patient analytics across the doctor's whole caseload."""
    doctor_id = _get_doctor_id(current_user)
    return await service.get_caseload_analytics(doctor_id)


# ── Patient List ─────────────────────────────────────────────

@router.get("/patients", response_model=schemas.PatientListResponse)
async def list_patients(
    current_user: Annotated[dict, Depends(role_required(UserRole.DOCTOR))]
):
    """List all patients assigned to this doctor."""
    doctor_id = _get_doctor_id(current_user)
    patients = await service.get_assigned_patients(doctor_id)
    return schemas.PatientListResponse(patients=patients, total=len(patients))


# ── Patient Detail ───────────────────────────────────────────

@router.get("/patients/{patient_id}", response_model=schemas.PatientDetail)
async def get_patient(
    patient_id: str,
    current_user: Annotated[dict, Depends(role_required(UserRole.DOCTOR))]
):
    """Get detailed info for an assigned patient."""
    doctor_id = _get_doctor_id(current_user)
    return await service.get_patient_detail(doctor_id, patient_id)


# ── Clinical Profile ─────────────────────────────────────────

@router.get(
    "/patients/{patient_id}/profile",
    response_model=schemas.PatientProfileResponse,
)
async def get_patient_profile(
    patient_id: str,
    current_user: Annotated[dict, Depends(role_required(UserRole.DOCTOR))],
):
    """Get an assigned patient's clinical profile."""
    doctor_id = _get_doctor_id(current_user)
    return await service.get_patient_profile(doctor_id, patient_id)


@router.put(
    "/patients/{patient_id}/profile",
    response_model=schemas.PatientProfileResponse,
)
async def update_patient_profile(
    patient_id: str,
    body: schemas.PatientProfileUpsert,
    request: Request,
    current_user: Annotated[dict, Depends(role_required(UserRole.DOCTOR))],
):
    """Create or update an assigned patient's clinical profile."""
    doctor_id = _get_doctor_id(current_user)
    changes = body.model_dump(exclude_unset=True)
    profile = await service.update_patient_profile(doctor_id, patient_id, changes)

    await log_action(
        user_id=doctor_id,
        action="updated_patient_profile",
        resource_type="patient_profile",
        resource_id=patient_id,
        details={"fields_updated": list(changes.keys())},
        ip_address=request.client.host if request.client else None,
    )

    return profile


# ── Recovery Score ───────────────────────────────────────────

@router.get(
    "/patients/{patient_id}/recovery-score",
    response_model=clinical_schemas.RecoveryScoreResponse,
)
async def get_patient_recovery_score(
    patient_id: str,
    current_user: Annotated[dict, Depends(role_required(UserRole.DOCTOR))],
    window_days: int = Query(30, ge=7, le=90),
):
    """Get an assigned patient's recovery score with its component breakdown."""
    doctor_id = _get_doctor_id(current_user)
    return await service.get_patient_recovery_score(doctor_id, patient_id, window_days)


# ── Digital Twin ─────────────────────────────────────────────

@router.get(
    "/patients/{patient_id}/digital-twin",
    response_model=clinical_schemas.DigitalTwinResponse,
)
async def get_patient_digital_twin(
    patient_id: str,
    current_user: Annotated[dict, Depends(role_required(UserRole.DOCTOR))],
    window_days: int = Query(30, ge=7, le=90),
    horizon_days: int = Query(30, ge=7, le=90),
):
    """Digital twin for an assigned patient: current state plus what-if projections."""
    doctor_id = _get_doctor_id(current_user)
    return await service.get_patient_digital_twin(
        doctor_id, patient_id, window_days, horizon_days
    )


# ── Check-ins ────────────────────────────────────────────────

@router.get(
    "/patients/{patient_id}/checkins",
    response_model=schemas.CheckinListResponse,
)
async def list_checkins(
    patient_id: str,
    current_user: Annotated[dict, Depends(role_required(UserRole.DOCTOR))],
    limit: int = Query(30, ge=1, le=100),
):
    """Get daily check-in history for a patient."""
    doctor_id = _get_doctor_id(current_user)
    checkins = await service.get_patient_checkins(doctor_id, patient_id, limit)
    return schemas.CheckinListResponse(checkins=checkins, total=len(checkins))


# ── Clinical Notes ───────────────────────────────────────────

@router.get(
    "/patients/{patient_id}/notes",
    response_model=schemas.ClinicalNoteListResponse,
)
async def list_notes(
    patient_id: str,
    current_user: Annotated[dict, Depends(role_required(UserRole.DOCTOR))],
):
    """Get all clinical notes for a patient."""
    doctor_id = _get_doctor_id(current_user)
    notes = await service.get_clinical_notes(doctor_id, patient_id)
    return schemas.ClinicalNoteListResponse(notes=notes, total=len(notes))


@router.post(
    "/patients/{patient_id}/notes",
    response_model=schemas.ClinicalNoteResponse,
    status_code=201,
)
async def create_note(
    patient_id: str,
    body: schemas.ClinicalNoteCreate,
    request: Request,
    current_user: Annotated[dict, Depends(role_required(UserRole.DOCTOR))],
):
    """Add a clinical note for a patient."""
    doctor_id = _get_doctor_id(current_user)
    note = await service.create_clinical_note(
        doctor_id, patient_id, body.model_dump()
    )

    await log_action(
        user_id=doctor_id,
        action="created_clinical_note",
        resource_type="clinical_note",
        resource_id=note["id"],
        details={"patient_id": patient_id, "note_type": body.note_type.value},
        ip_address=request.client.host if request.client else None,
    )

    return note


# ── Recovery Goals ───────────────────────────────────────────

@router.get(
    "/patients/{patient_id}/goals",
    response_model=schemas.RecoveryGoalListResponse,
)
async def list_goals(
    patient_id: str,
    current_user: Annotated[dict, Depends(role_required(UserRole.DOCTOR))],
):
    """Get all recovery goals for a patient."""
    doctor_id = _get_doctor_id(current_user)
    goals = await service.get_recovery_goals(doctor_id, patient_id)
    return schemas.RecoveryGoalListResponse(goals=goals, total=len(goals))


@router.post(
    "/patients/{patient_id}/goals",
    response_model=schemas.RecoveryGoalResponse,
    status_code=201,
)
async def create_goal(
    patient_id: str,
    body: schemas.RecoveryGoalCreate,
    request: Request,
    current_user: Annotated[dict, Depends(role_required(UserRole.DOCTOR))],
):
    """Create a recovery goal for a patient."""
    doctor_id = _get_doctor_id(current_user)
    goal = await service.create_recovery_goal(
        doctor_id, patient_id, body.model_dump()
    )

    await log_action(
        user_id=doctor_id,
        action="created_recovery_goal",
        resource_type="recovery_goal",
        resource_id=goal["id"],
        details={"patient_id": patient_id, "title": body.title},
        ip_address=request.client.host if request.client else None,
    )

    return goal


@router.patch(
    "/patients/{patient_id}/goals/{goal_id}",
    response_model=schemas.RecoveryGoalResponse,
)
async def update_goal(
    patient_id: str,
    goal_id: str,
    body: schemas.RecoveryGoalUpdate,
    request: Request,
    current_user: Annotated[dict, Depends(role_required(UserRole.DOCTOR))],
):
    """Update a recovery goal's status or notes."""
    doctor_id = _get_doctor_id(current_user)
    goal = await service.update_recovery_goal(
        doctor_id, patient_id, goal_id, body.model_dump(exclude_unset=True)
    )

    await log_action(
        user_id=doctor_id,
        action="updated_recovery_goal",
        resource_type="recovery_goal",
        resource_id=goal_id,
        details={
            "patient_id": patient_id,
            "fields_updated": list(body.model_dump(exclude_unset=True).keys()),
        },
        ip_address=request.client.host if request.client else None,
    )

    return goal
