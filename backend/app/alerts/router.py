from fastapi import APIRouter, Depends, Query
from typing import Annotated

from app.auth.dependencies import get_current_user
from app.alerts import schemas, service
from app.common.alerts import maybe_scan_missed_checkins

router = APIRouter(prefix="/alerts", tags=["Alerts"])


# ── Alert Listing ────────────────────────────────────────────

@router.get("", response_model=schemas.AlertListResponse)
async def list_alerts(
    current_user: Annotated[dict, Depends(get_current_user)],
    unread_only: bool = Query(False, description="Return only unread alerts"),
    limit: int = Query(50, ge=1, le=200),
):
    """Get clinical alerts targeted at the authenticated user, newest first."""
    # Opportunistic (throttled) sweep so missed check-ins surface without a cron
    await maybe_scan_missed_checkins()

    alerts, unread = await service.list_alerts(
        current_user["id"], unread_only, limit
    )
    return schemas.AlertListResponse(
        alerts=alerts, total=len(alerts), unread=unread
    )


@router.get("/unread-count", response_model=schemas.UnreadCountResponse)
async def get_unread_count(
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Get the badge count of unread alerts for the notification bell."""
    unread = await service.count_unread(current_user["id"])
    return schemas.UnreadCountResponse(unread=unread)


# ── Mark as Read ─────────────────────────────────────────────

@router.patch("/read-all", response_model=schemas.MarkReadResponse)
async def mark_all_alerts_read(
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Mark every unread alert for the authenticated user as read."""
    updated = await service.mark_all_read(current_user["id"])
    return schemas.MarkReadResponse(
        message=f"{updated} alert(s) marked as read", updated=updated
    )


@router.patch("/{alert_id}/read", response_model=schemas.MarkReadResponse)
async def mark_alert_read(
    alert_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Mark a single alert as read."""
    updated = await service.mark_alert_read(current_user["id"], alert_id)
    return schemas.MarkReadResponse(message="Alert marked as read", updated=updated)
