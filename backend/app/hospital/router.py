from fastapi import APIRouter, Depends, Request, Query
from typing import Annotated, Optional

from app.auth.schemas import UserRole
from app.auth.dependencies import role_required
from app.hospital import schemas, service
from app.common.audit import log_action
from app.common.audit import (
    query_audit_logs,
    get_audit_facets,
    AuditLogListResponse,
    AuditFacetsResponse,
)

router = APIRouter(prefix="/hospital", tags=["Hospital"])


def _get_hospital_id(user: dict) -> str:
    """Extract the hospital_id from the authenticated hospital admin user."""
    return user.get("hospital_id")


# ── Hospital Dashboard Stats ────────────────────────────────

@router.get("/dashboard", response_model=schemas.HospitalDashboardStats)
async def get_dashboard(
    current_user: Annotated[dict, Depends(role_required(UserRole.HOSPITAL))]
):
    """Get hospital-specific dashboard stats."""
    hospital_id = _get_hospital_id(current_user)
    return await service.get_hospital_dashboard_stats(hospital_id)


# ── User Management ─────────────────────────────────────────

@router.get("/users", response_model=schemas.UserListResponse)
async def list_users(
    current_user: Annotated[dict, Depends(role_required(UserRole.HOSPITAL))],
    role: Optional[str] = Query(None, description="Filter by role: doctor, patient, guardian"),
):
    """List all users belonging to this hospital."""
    hospital_id = _get_hospital_id(current_user)
    users = await service.get_hospital_users(hospital_id, role_filter=role)
    return schemas.UserListResponse(users=users, total=len(users))


@router.post("/users", response_model=schemas.HospitalUserResponse, status_code=201)
async def create_user(
    body: schemas.UserCreate,
    request: Request,
    current_user: Annotated[dict, Depends(role_required(UserRole.HOSPITAL))],
):
    """Create a doctor, patient, or guardian under this hospital."""
    hospital_id = _get_hospital_id(current_user)
    user = await service.create_hospital_user(hospital_id, body.model_dump())

    await log_action(
        user_id=current_user["id"],
        action=f"created_{body.role.value}",
        resource_type="user",
        resource_id=user["id"],
        details={"user_name": user["full_name"], "role": body.role.value},
        ip_address=request.client.host if request.client else None,
    )

    return user


@router.put("/users/{user_id}", response_model=schemas.HospitalUserResponse)
async def update_user(
    user_id: str,
    body: schemas.UserUpdate,
    request: Request,
    current_user: Annotated[dict, Depends(role_required(UserRole.HOSPITAL))],
):
    """Update a user belonging to this hospital."""
    hospital_id = _get_hospital_id(current_user)
    user = await service.update_hospital_user(
        hospital_id, user_id, body.model_dump(exclude_unset=True)
    )

    await log_action(
        user_id=current_user["id"],
        action="updated_user",
        resource_type="user",
        resource_id=user_id,
        details={"fields_updated": list(body.model_dump(exclude_unset=True).keys())},
        ip_address=request.client.host if request.client else None,
    )

    return user


@router.patch("/users/{user_id}/status", response_model=schemas.HospitalUserResponse)
async def toggle_user_status(
    user_id: str,
    body: schemas.UserStatusUpdate,
    request: Request,
    current_user: Annotated[dict, Depends(role_required(UserRole.HOSPITAL))],
):
    """Activate or deactivate a user belonging to this hospital."""
    hospital_id = _get_hospital_id(current_user)
    user = await service.update_hospital_user_status(hospital_id, user_id, body.is_active)

    await log_action(
        user_id=current_user["id"],
        action="activated_user" if body.is_active else "deactivated_user",
        resource_type="user",
        resource_id=user_id,
        ip_address=request.client.host if request.client else None,
    )

    return user


# ── Audit Trail ──────────────────────────────────────────────

@router.get("/audit-logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    current_user: Annotated[dict, Depends(role_required(UserRole.HOSPITAL))],
    action: Optional[str] = Query(None, description="Exact action name"),
    resource_type: Optional[str] = Query(None, description="e.g. user, medication"),
    actor_id: Optional[str] = Query(None, description="Filter to one actor"),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD, inclusive"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD, inclusive"),
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
):
    """Read this hospital's audit trail — actions taken by its own users only."""
    hospital_id = _get_hospital_id(current_user)
    return await query_audit_logs(
        hospital_id=hospital_id,
        action=action,
        resource_type=resource_type,
        actor_id=actor_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        skip=skip,
    )


@router.get("/audit-logs/facets", response_model=AuditFacetsResponse)
async def get_audit_log_facets(
    current_user: Annotated[dict, Depends(role_required(UserRole.HOSPITAL))],
):
    """Distinct actions and resource types within this hospital."""
    hospital_id = _get_hospital_id(current_user)
    return await get_audit_facets(hospital_id=hospital_id)


# ── Patient Clinical Profile ─────────────────────────────────

@router.get("/patients/{patient_id}/profile", response_model=schemas.PatientProfileResponse)
async def get_patient_profile(
    patient_id: str,
    current_user: Annotated[dict, Depends(role_required(UserRole.HOSPITAL))],
):
    """Get the clinical profile of a patient in this hospital."""
    hospital_id = _get_hospital_id(current_user)
    return await service.get_patient_profile(hospital_id, patient_id)


@router.put("/patients/{patient_id}/profile", response_model=schemas.PatientProfileResponse)
async def update_patient_profile(
    patient_id: str,
    body: schemas.PatientProfileUpsert,
    request: Request,
    current_user: Annotated[dict, Depends(role_required(UserRole.HOSPITAL))],
):
    """Create or update the clinical profile of a patient in this hospital."""
    hospital_id = _get_hospital_id(current_user)
    changes = body.model_dump(exclude_unset=True)
    profile = await service.update_patient_profile(
        hospital_id, patient_id, changes, updated_by=current_user["id"]
    )

    await log_action(
        user_id=current_user["id"],
        action="updated_patient_profile",
        resource_type="patient_profile",
        resource_id=patient_id,
        details={"fields_updated": list(changes.keys())},
        ip_address=request.client.host if request.client else None,
    )

    return profile


# ── Doctor-Patient Assignments ───────────────────────────────

@router.get("/assignments", response_model=schemas.AssignmentListResponse)
async def list_assignments(
    current_user: Annotated[dict, Depends(role_required(UserRole.HOSPITAL))],
):
    """List all doctor-patient assignments for this hospital."""
    hospital_id = _get_hospital_id(current_user)
    assignments = await service.get_assignments(hospital_id)
    return schemas.AssignmentListResponse(assignments=assignments, total=len(assignments))


@router.post("/assignments", response_model=schemas.AssignmentResponse, status_code=201)
async def create_assignment(
    body: schemas.AssignmentCreate,
    request: Request,
    current_user: Annotated[dict, Depends(role_required(UserRole.HOSPITAL))],
):
    """Assign a doctor to a patient."""
    hospital_id = _get_hospital_id(current_user)
    assignment = await service.create_assignment(hospital_id, body.doctor_id, body.patient_id)

    await log_action(
        user_id=current_user["id"],
        action="created_assignment",
        resource_type="assignment",
        resource_id=assignment["id"],
        details={
            "doctor_name": assignment["doctor_name"],
            "patient_name": assignment["patient_name"],
        },
        ip_address=request.client.host if request.client else None,
    )

    return assignment


@router.delete("/assignments/{assignment_id}", response_model=schemas.MessageResponse)
async def delete_assignment(
    assignment_id: str,
    request: Request,
    current_user: Annotated[dict, Depends(role_required(UserRole.HOSPITAL))],
):
    """Remove a doctor-patient assignment."""
    hospital_id = _get_hospital_id(current_user)
    await service.remove_assignment(hospital_id, assignment_id)

    await log_action(
        user_id=current_user["id"],
        action="removed_assignment",
        resource_type="assignment",
        resource_id=assignment_id,
        ip_address=request.client.host if request.client else None,
    )

    return schemas.MessageResponse(message="Assignment removed successfully")


# ── Guardian Linking ─────────────────────────────────────────

@router.post("/link-guardian", response_model=schemas.GuardianLinkResponse, status_code=201)
async def link_guardian(
    body: schemas.GuardianLinkRequest,
    request: Request,
    current_user: Annotated[dict, Depends(role_required(UserRole.HOSPITAL))],
):
    """Link a guardian to a patient."""
    hospital_id = _get_hospital_id(current_user)
    result = await service.link_guardian(hospital_id, body.guardian_id, body.patient_id)

    await log_action(
        user_id=current_user["id"],
        action="linked_guardian",
        resource_type="guardian_link",
        details={
            "guardian_name": result["guardian_name"],
            "patient_name": result["patient_name"],
        },
        ip_address=request.client.host if request.client else None,
    )

    return result


@router.delete("/unlink-guardian/{guardian_id}", response_model=schemas.MessageResponse)
async def unlink_guardian(
    guardian_id: str,
    request: Request,
    current_user: Annotated[dict, Depends(role_required(UserRole.HOSPITAL))],
):
    """Remove the guardian-patient link."""
    hospital_id = _get_hospital_id(current_user)
    await service.unlink_guardian(hospital_id, guardian_id)

    await log_action(
        user_id=current_user["id"],
        action="unlinked_guardian",
        resource_type="guardian_link",
        resource_id=guardian_id,
        ip_address=request.client.host if request.client else None,
    )

    return schemas.MessageResponse(message="Guardian unlinked successfully")
