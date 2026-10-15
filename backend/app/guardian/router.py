from fastapi import APIRouter, Depends
from typing import Annotated

from app.auth.schemas import UserRole
from app.auth.dependencies import role_required
from app.guardian import schemas, service

router = APIRouter(prefix="/guardian", tags=["Guardian"])


def _get_guardian_id(user: dict) -> str:
    """Extract the guardian's user ID."""
    return user.get("id")


# ── Dashboard ────────────────────────────────────────────────

@router.get("/dashboard", response_model=schemas.GuardianDashboardResponse)
async def get_dashboard(
    current_user: Annotated[dict, Depends(role_required(UserRole.GUARDIAN))]
):
    """Get guardian dashboard: linked patient summary, vitals, alerts."""
    guardian_id = _get_guardian_id(current_user)
    return await service.get_guardian_dashboard(guardian_id)


# ── Patient Overview ─────────────────────────────────────────

@router.get("/patient", response_model=schemas.PatientOverviewResponse)
async def get_patient_overview(
    current_user: Annotated[dict, Depends(role_required(UserRole.GUARDIAN))]
):
    """Get detailed read-only view of the linked patient's recovery data."""
    guardian_id = _get_guardian_id(current_user)
    return await service.get_patient_overview(guardian_id)
