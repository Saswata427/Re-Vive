from fastapi import APIRouter, Depends, Request, Query
from typing import Annotated, Optional

from app.auth.schemas import UserRole
from app.auth.dependencies import get_current_user, role_required
from app.appointments import schemas, service
from app.common.audit import log_action

router = APIRouter(prefix="/appointments", tags=["Appointments"])


# ── Listing ──────────────────────────────────────────────────

@router.get("", response_model=schemas.AppointmentListResponse)
async def list_appointments(
    current_user: Annotated[dict, Depends(get_current_user)],
    status: Optional[str] = Query(
        None, description="Filter by status: scheduled, completed, cancelled"
    ),
    upcoming_only: bool = Query(False, description="Only future scheduled visits"),
    limit: int = Query(100, ge=1, le=200),
):
    """List appointments visible to the authenticated user, scoped by role."""
    appointments, upcoming = await service.list_appointments(
        current_user, status_filter=status, upcoming_only=upcoming_only, limit=limit
    )
    return schemas.AppointmentListResponse(
        appointments=appointments, total=len(appointments), upcoming=upcoming
    )


@router.get("/{appointment_id}", response_model=schemas.AppointmentResponse)
async def get_appointment(
    appointment_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Get a single appointment."""
    return await service.get_appointment(current_user, appointment_id)


# ── Creation ─────────────────────────────────────────────────

@router.post("", response_model=schemas.AppointmentResponse, status_code=201)
async def create_appointment(
    body: schemas.AppointmentCreate,
    request: Request,
    current_user: Annotated[dict, Depends(role_required(UserRole.DOCTOR))],
):
    """Schedule an appointment with one of the doctor's assigned patients."""
    doctor_id = current_user["id"]
    appointment = await service.create_appointment(doctor_id, body.model_dump())

    await log_action(
        user_id=doctor_id,
        action="scheduled_appointment",
        resource_type="appointment",
        resource_id=appointment["id"],
        details={
            "patient_id": body.patient_id,
            "date_time": body.date_time.isoformat(),
            "reason": body.reason,
        },
        ip_address=request.client.host if request.client else None,
    )

    return appointment


# ── Updates ──────────────────────────────────────────────────

@router.patch("/{appointment_id}", response_model=schemas.AppointmentResponse)
async def update_appointment(
    appointment_id: str,
    body: schemas.AppointmentUpdate,
    request: Request,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Reschedule, complete, cancel, or annotate an appointment."""
    changes = body.model_dump(exclude_unset=True)
    appointment = await service.update_appointment(
        current_user, appointment_id, changes
    )

    await log_action(
        user_id=current_user["id"],
        action="updated_appointment",
        resource_type="appointment",
        resource_id=appointment_id,
        details={"fields_updated": list(changes.keys())},
        ip_address=request.client.host if request.client else None,
    )

    return appointment
