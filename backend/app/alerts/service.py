from bson import ObjectId

from app.database import get_db
from app.common.models import serialize_doc, to_object_id
from app.common.exceptions import NotFoundError


# ── Helpers ──────────────────────────────────────────────────

async def _resolve_patient_names(patient_oids: list[ObjectId]) -> dict[str, str]:
    """Batch-resolve patient IDs to display names, keyed by string ID."""
    db = get_db()
    if not patient_oids:
        return {}

    names: dict[str, str] = {}
    cursor = db.users.find(
        {"_id": {"$in": patient_oids}},
        {"full_name": 1},
    )
    async for user in cursor:
        names[str(user["_id"])] = user.get("full_name", "Patient")

    return names


# ── Alert Listing ────────────────────────────────────────────

async def list_alerts(
    user_id: str, unread_only: bool = False, limit: int = 50
) -> tuple[list[dict], int]:
    """Get alerts targeted at a user, newest first. Returns (alerts, unread_count)."""
    db = get_db()
    user_oid = to_object_id(user_id)

    query: dict = {"target_user_id": user_oid}
    if unread_only:
        query["is_read"] = False

    raw = (
        await db.alerts.find(query)
        .sort("created_at", -1)
        .to_list(length=limit)
    )

    # Collect distinct patient IDs for name enrichment
    patient_oids = []
    for alert in raw:
        pid = alert.get("patient_id")
        if isinstance(pid, ObjectId) and pid not in patient_oids:
            patient_oids.append(pid)

    names = await _resolve_patient_names(patient_oids)

    alerts = []
    for alert in raw:
        doc = serialize_doc(alert)
        doc["patient_name"] = names.get(doc.get("patient_id"))
        alerts.append(doc)

    unread = await count_unread(user_id)

    return alerts, unread


async def count_unread(user_id: str) -> int:
    """Count a user's unread alerts."""
    db = get_db()
    return await db.alerts.count_documents({
        "target_user_id": to_object_id(user_id),
        "is_read": False,
    })


# ── Mark as Read ─────────────────────────────────────────────

async def mark_alert_read(user_id: str, alert_id: str) -> int:
    """Mark one of the user's own alerts as read. Returns the modified count."""
    db = get_db()
    result = await db.alerts.update_one(
        {
            "_id": to_object_id(alert_id),
            "target_user_id": to_object_id(user_id),
        },
        {"$set": {"is_read": True}},
    )

    if result.matched_count == 0:
        raise NotFoundError("Alert")

    return result.modified_count


async def mark_all_read(user_id: str) -> int:
    """Mark every unread alert for the user as read. Returns the modified count."""
    db = get_db()
    result = await db.alerts.update_many(
        {"target_user_id": to_object_id(user_id), "is_read": False},
        {"$set": {"is_read": True}},
    )
    return result.modified_count
