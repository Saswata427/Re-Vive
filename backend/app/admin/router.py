from fastapi import APIRouter, Depends, Request, Query
from typing import Annotated, Optional

from app.auth.schemas import UserRole
from app.auth.dependencies import role_required
from app.admin import schemas, service
from app.common.audit import log_action
from app.common.audit import (
    query_audit_logs,
    get_audit_facets,
    AuditLogListResponse,
    AuditFacetsResponse,
)

router = APIRouter(prefix="/admin", tags=["Admin"])


# ── Platform Statistics ──────────────────────────────────────

@router.get("/stats", response_model=schemas.PlatformStatsResponse)
async def get_stats(
    current_user: Annotated[dict, Depends(role_required(UserRole.ADMIN))]
):
    """Get platform-wide statistics (admin only)."""
    return await service.get_platform_stats()


# ── Audit Trail ──────────────────────────────────────────────

@router.get("/audit-logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    current_user: Annotated[dict, Depends(role_required(UserRole.ADMIN))],
    action: Optional[str] = Query(None, description="Exact action name"),
    resource_type: Optional[str] = Query(None, description="e.g. user, medication"),
    actor_id: Optional[str] = Query(None, description="Filter to one actor"),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD, inclusive"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD, inclusive"),
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
):
    """Read the platform-wide audit trail, newest first."""
    return await query_audit_logs(
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
    current_user: Annotated[dict, Depends(role_required(UserRole.ADMIN))],
):
    """Distinct actions and resource types, for the filter dropdowns."""
    return await get_audit_facets()


# ── Hospital Admin Management ────────────────────────────────
# Registered before /hospitals/{hospital_id} so this literal path matches first.

@router.get("/hospital-admins", response_model=schemas.HospitalAdminListResponse)
async def list_hospital_admins(
    current_user: Annotated[dict, Depends(role_required(UserRole.ADMIN))]
):
    """List every hospital admin account across the platform."""
    admins = await service.get_hospital_admins()
    return schemas.HospitalAdminListResponse(admins=admins, total=len(admins))


@router.get("/hospitals/{hospital_id}/admin", response_model=schemas.HospitalAdminResponse)
async def get_hospital_admin(
    hospital_id: str,
    current_user: Annotated[dict, Depends(role_required(UserRole.ADMIN))],
):
    """Get the admin account for one hospital."""
    return await service.get_hospital_admin(hospital_id)


@router.put("/hospitals/{hospital_id}/admin", response_model=schemas.HospitalAdminResponse)
async def update_hospital_admin(
    hospital_id: str,
    body: schemas.HospitalAdminUpdate,
    request: Request,
    current_user: Annotated[dict, Depends(role_required(UserRole.ADMIN))],
):
    """Update the hospital admin's name, email, or phone."""
    changes = body.model_dump(exclude_unset=True)
    admin = await service.update_hospital_admin(hospital_id, changes)

    await log_action(
        user_id=current_user["id"],
        action="updated_hospital_admin",
        resource_type="user",
        resource_id=admin["id"],
        details={"hospital_id": hospital_id, "fields_updated": list(changes.keys())},
        ip_address=request.client.host if request.client else None,
    )

    return admin


@router.patch(
    "/hospitals/{hospital_id}/admin/password",
    response_model=schemas.HospitalAdminResponse,
)
async def reset_hospital_admin_password(
    hospital_id: str,
    body: schemas.HospitalAdminPasswordReset,
    request: Request,
    current_user: Annotated[dict, Depends(role_required(UserRole.ADMIN))],
):
    """Set a new password for the hospital admin."""
    admin = await service.reset_hospital_admin_password(hospital_id, body.new_password)

    await log_action(
        user_id=current_user["id"],
        action="reset_hospital_admin_password",
        resource_type="user",
        resource_id=admin["id"],
        details={"hospital_id": hospital_id},
        ip_address=request.client.host if request.client else None,
    )

    return admin


@router.post(
    "/hospitals/{hospital_id}/admin",
    response_model=schemas.HospitalAdminResponse,
    status_code=201,
)
async def replace_hospital_admin(
    hospital_id: str,
    body: schemas.HospitalAdminReplace,
    request: Request,
    current_user: Annotated[dict, Depends(role_required(UserRole.ADMIN))],
):
    """Hand the hospital over to a new admin. The outgoing admin is deactivated."""
    admin = await service.replace_hospital_admin(hospital_id, body.model_dump())

    await log_action(
        user_id=current_user["id"],
        action="replaced_hospital_admin",
        resource_type="user",
        resource_id=admin["id"],
        details={"hospital_id": hospital_id, "new_admin_email": body.admin_email},
        ip_address=request.client.host if request.client else None,
    )

    return admin


# ── Hospital CRUD ────────────────────────────────────────────

@router.get("/hospitals", response_model=schemas.HospitalListResponse)
async def list_hospitals(
    current_user: Annotated[dict, Depends(role_required(UserRole.ADMIN))]
):
    """Get all hospitals."""
    hospitals = await service.get_all_hospitals()
    return schemas.HospitalListResponse(hospitals=hospitals, total=len(hospitals))


@router.post("/hospitals", response_model=schemas.HospitalResponse, status_code=201)
async def create_hospital(
    body: schemas.HospitalCreate,
    request: Request,
    current_user: Annotated[dict, Depends(role_required(UserRole.ADMIN))]
):
    """Create a new hospital with an admin user account."""
    hospital = await service.create_hospital(body.model_dump())

    await log_action(
        user_id=current_user["id"],
        action="created_hospital",
        resource_type="hospital",
        resource_id=hospital["id"],
        details={"hospital_name": hospital["name"]},
        ip_address=request.client.host if request.client else None,
    )

    return hospital


@router.get("/hospitals/{hospital_id}", response_model=schemas.HospitalResponse)
async def get_hospital(
    hospital_id: str,
    current_user: Annotated[dict, Depends(role_required(UserRole.ADMIN))]
):
    """Get a single hospital by ID."""
    return await service.get_hospital_by_id(hospital_id)


@router.put("/hospitals/{hospital_id}", response_model=schemas.HospitalResponse)
async def update_hospital(
    hospital_id: str,
    body: schemas.HospitalUpdate,
    request: Request,
    current_user: Annotated[dict, Depends(role_required(UserRole.ADMIN))]
):
    """Update hospital details."""
    hospital = await service.update_hospital(hospital_id, body.model_dump(exclude_unset=True))

    await log_action(
        user_id=current_user["id"],
        action="updated_hospital",
        resource_type="hospital",
        resource_id=hospital_id,
        details={"fields_updated": list(body.model_dump(exclude_unset=True).keys())},
        ip_address=request.client.host if request.client else None,
    )

    return hospital


@router.patch("/hospitals/{hospital_id}/status", response_model=schemas.HospitalResponse)
async def toggle_hospital_status(
    hospital_id: str,
    body: schemas.HospitalStatusUpdate,
    request: Request,
    current_user: Annotated[dict, Depends(role_required(UserRole.ADMIN))]
):
    """Activate or deactivate a hospital."""
    hospital = await service.update_hospital_status(hospital_id, body.is_active)

    await log_action(
        user_id=current_user["id"],
        action="activated_hospital" if body.is_active else "deactivated_hospital",
        resource_type="hospital",
        resource_id=hospital_id,
        ip_address=request.client.host if request.client else None,
    )

    return hospital
