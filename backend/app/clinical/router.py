from fastapi import APIRouter, Depends, Request, Query
from typing import Annotated

from app.auth.dependencies import get_current_user
from app.clinical import schemas, service
from app.common import recovery
from app.common.audit import log_action

router = APIRouter(prefix="/clinical", tags=["Clinical Record"])


# ── Medications ──────────────────────────────────────────────

@router.get(
    "/patients/{patient_id}/medications",
    response_model=schemas.MedicationListResponse,
)
async def list_medications(
    patient_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """List a patient's medications. Readable by their care team and the patient."""
    patient_oid = await service.resolve_patient_access(current_user, patient_id)
    medications, active = await service.list_medications(patient_oid)
    return schemas.MedicationListResponse(
        medications=medications, total=len(medications), active=active
    )


@router.post(
    "/patients/{patient_id}/medications",
    response_model=schemas.MedicationResponse,
    status_code=201,
)
async def create_medication(
    patient_id: str,
    body: schemas.MedicationCreate,
    request: Request,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Prescribe a medication. Doctor only, for an assigned patient."""
    patient_oid = await service.require_doctor_for_patient(current_user, patient_id)
    medication = await service.create_medication(
        patient_oid, current_user["id"], body.model_dump()
    )

    await log_action(
        user_id=current_user["id"],
        action="prescribed_medication",
        resource_type="medication",
        resource_id=medication["id"],
        details={"patient_id": patient_id, "name": body.name},
        ip_address=request.client.host if request.client else None,
    )

    return medication


@router.patch(
    "/patients/{patient_id}/medications/{medication_id}",
    response_model=schemas.MedicationResponse,
)
async def update_medication(
    patient_id: str,
    medication_id: str,
    body: schemas.MedicationUpdate,
    request: Request,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Update or discontinue a medication. Doctor only."""
    patient_oid = await service.require_doctor_for_patient(current_user, patient_id)
    changes = body.model_dump(exclude_unset=True)
    medication = await service.update_medication(patient_oid, medication_id, changes)

    await log_action(
        user_id=current_user["id"],
        action="updated_medication",
        resource_type="medication",
        resource_id=medication_id,
        details={"patient_id": patient_id, "fields_updated": list(changes.keys())},
        ip_address=request.client.host if request.client else None,
    )

    return medication


# ── Vitals ───────────────────────────────────────────────────

@router.get(
    "/patients/{patient_id}/vitals",
    response_model=schemas.VitalsListResponse,
)
async def list_vitals(
    patient_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    limit: int = Query(50, ge=1, le=200),
):
    """List a patient's recorded vitals, most recent first."""
    patient_oid = await service.resolve_patient_access(current_user, patient_id)
    vitals = await service.list_vitals(patient_oid, limit)
    return schemas.VitalsListResponse(vitals=vitals, total=len(vitals))


@router.post(
    "/patients/{patient_id}/vitals",
    response_model=schemas.VitalsResponse,
    status_code=201,
)
async def create_vitals(
    patient_id: str,
    body: schemas.VitalsCreate,
    request: Request,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Record a set of vital signs. Doctor only, for an assigned patient."""
    patient_oid = await service.require_doctor_for_patient(current_user, patient_id)
    vitals = await service.create_vitals(
        patient_oid, current_user["id"], body.model_dump()
    )

    await log_action(
        user_id=current_user["id"],
        action="recorded_vitals",
        resource_type="vitals",
        resource_id=vitals["id"],
        details={"patient_id": patient_id},
        ip_address=request.client.host if request.client else None,
    )

    return vitals


# ── Interventions ────────────────────────────────────────────

@router.get(
    "/patients/{patient_id}/interventions",
    response_model=schemas.InterventionListResponse,
)
async def list_interventions(
    patient_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """List a patient's recorded interventions, newest first."""
    patient_oid = await service.resolve_patient_access(current_user, patient_id)
    interventions, pending = await service.list_interventions(patient_oid)
    return schemas.InterventionListResponse(
        interventions=interventions,
        total=len(interventions),
        pending_outcomes=pending,
    )


@router.post(
    "/patients/{patient_id}/interventions",
    response_model=schemas.InterventionResponse,
    status_code=201,
)
async def create_intervention(
    patient_id: str,
    body: schemas.InterventionCreate,
    request: Request,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Record an intervention (doctor only); a linked alert is marked read."""
    patient_oid = await service.require_doctor_for_patient(current_user, patient_id)
    intervention = await service.create_intervention(
        patient_oid, current_user["id"], body.model_dump()
    )

    await log_action(
        user_id=current_user["id"],
        action="recorded_intervention",
        resource_type="intervention",
        resource_id=intervention["id"],
        details={
            "patient_id": patient_id,
            "intervention_type": body.intervention_type.value,
            "linked_alert": body.alert_id,
        },
        ip_address=request.client.host if request.client else None,
    )

    return intervention


@router.patch(
    "/patients/{patient_id}/interventions/{intervention_id}",
    response_model=schemas.InterventionResponse,
)
async def update_intervention(
    patient_id: str,
    intervention_id: str,
    body: schemas.InterventionUpdate,
    request: Request,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Record an intervention's outcome, or amend it. Doctor only."""
    patient_oid = await service.require_doctor_for_patient(current_user, patient_id)
    changes = body.model_dump(exclude_unset=True)
    intervention = await service.update_intervention(
        patient_oid, intervention_id, changes
    )

    await log_action(
        user_id=current_user["id"],
        action="updated_intervention",
        resource_type="intervention",
        resource_id=intervention_id,
        details={"patient_id": patient_id, "fields_updated": list(changes.keys())},
        ip_address=request.client.host if request.client else None,
    )

    return intervention


# ── Treatment Plan ───────────────────────────────────────────

@router.get(
    "/patients/{patient_id}/treatment-plan",
    response_model=schemas.TreatmentPlanHistoryResponse,
)
async def get_treatment_plan(
    patient_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Get the current care plan plus every superseded version."""
    patient_oid = await service.resolve_patient_access(current_user, patient_id)
    return await service.get_treatment_plan(patient_oid)


@router.put(
    "/patients/{patient_id}/treatment-plan",
    response_model=schemas.TreatmentPlanResponse,
    status_code=201,
)
async def upsert_treatment_plan(
    patient_id: str,
    body: schemas.TreatmentPlanUpsert,
    request: Request,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Publish a new care plan version (doctor only)."""
    patient_oid = await service.require_doctor_for_patient(current_user, patient_id)
    plan = await service.upsert_treatment_plan(
        patient_oid, current_user["id"], body.model_dump()
    )

    await log_action(
        user_id=current_user["id"],
        action="published_treatment_plan",
        resource_type="treatment_plan",
        resource_id=plan["id"],
        details={"patient_id": patient_id, "version": plan["version"]},
        ip_address=request.client.host if request.client else None,
    )

    return plan


# ── Aggregated Medical History ───────────────────────────────

@router.get(
    "/patients/{patient_id}/history",
    response_model=schemas.MedicalHistoryResponse,
)
async def get_medical_history(
    patient_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    limit: int = Query(100, ge=1, le=300),
):
    """Get the merged longitudinal record: check-ins, notes, goals, meds, vitals, appointments."""
    patient_oid = await service.resolve_patient_access(current_user, patient_id)
    return await service.get_medical_history(patient_oid, limit)


# ── Recovery Score & Timeline ────────────────────────────────

@router.get(
    "/patients/{patient_id}/recovery-score",
    response_model=schemas.RecoveryScoreResponse,
)
async def get_recovery_score(
    patient_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    window_days: int = Query(30, ge=7, le=90),
):
    """Get a patient's 0-100 recovery score with its component breakdown."""
    patient_oid = await service.resolve_patient_access(current_user, patient_id)
    return await recovery.calculate_recovery_score(patient_oid, window_days)


@router.get(
    "/patients/{patient_id}/timeline",
    response_model=schemas.RecoveryTimelineResponse,
)
async def get_recovery_timeline(
    patient_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    days: int = Query(30, ge=7, le=90),
):
    """Get the longitudinal record grouped by day with point-in-time daily scores."""
    patient_oid = await service.resolve_patient_access(current_user, patient_id)
    return await recovery.get_recovery_timeline(patient_oid, days)


# ── Digital Twin ─────────────────────────────────────────────

@router.get(
    "/patients/{patient_id}/digital-twin",
    response_model=schemas.DigitalTwinResponse,
)
async def get_digital_twin(
    patient_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    window_days: int = Query(30, ge=7, le=90),
    horizon_days: int = Query(30, ge=7, le=90),
):
    """Digital twin: the current state plus what-if projections."""
    patient_oid = await service.resolve_patient_access(current_user, patient_id)
    return await recovery.build_digital_twin(patient_oid, window_days, horizon_days)
