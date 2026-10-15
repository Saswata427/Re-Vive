"""Audit trail: write from anywhere, read platform-wide or per hospital."""

from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId
from pydantic import BaseModel, Field

from app.database import get_db
from app.common.models import to_object_id


# ── Writing ──────────────────────────────────────────────────

async def log_action(
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: str = None,
    details: dict = None,
    ip_address: str = None,
):
    """Write one audit log entry."""
    db = get_db()
    await db.audit_logs.insert_one({
        "user_id": user_id,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "details": details or {},
        "ip_address": ip_address,
        "created_at": datetime.now(timezone.utc),
    })


# ── Reading ──────────────────────────────────────────────────

async def _actor_names(user_ids: list[str]) -> dict[str, dict]:
    """Resolve actor IDs to name/role/email for display."""
    db = get_db()

    oids = []
    for uid in user_ids:
        if uid and ObjectId.is_valid(str(uid)):
            oids.append(ObjectId(str(uid)))
    if not oids:
        return {}

    actors = {}
    async for user in db.users.find(
        {"_id": {"$in": oids}}, {"full_name": 1, "role": 1, "email": 1}
    ):
        actors[str(user["_id"])] = {
            "full_name": user.get("full_name"),
            "role": user.get("role"),
            "email": user.get("email"),
        }
    return actors


async def query_audit_logs(
    hospital_id: str = None,
    action: str = None,
    resource_type: str = None,
    actor_id: str = None,
    date_from: str = None,
    date_to: str = None,
    limit: int = 50,
    skip: int = 0,
) -> dict:
    """Read the audit trail with filters; `hospital_id` limits it to that hospital's users."""
    db = get_db()
    query: dict = {}

    # Hospital scope: resolve that hospital's users, then filter to their actions
    if hospital_id is not None:
        member_ids = []
        async for user in db.users.find(
            {"hospital_id": to_object_id(hospital_id)}, {"_id": 1}
        ):
            member_ids.append(str(user["_id"]))
        if not member_ids:
            return {"logs": [], "total": 0, "limit": limit, "skip": skip}
        query["user_id"] = {"$in": member_ids}

    if actor_id:
        # An explicit actor must still sit inside the hospital scope
        if "user_id" in query and actor_id not in query["user_id"]["$in"]:
            return {"logs": [], "total": 0, "limit": limit, "skip": skip}
        query["user_id"] = actor_id

    if action:
        query["action"] = action
    if resource_type:
        query["resource_type"] = resource_type

    date_filter = {}
    if date_from:
        try:
            date_filter["$gte"] = datetime.fromisoformat(date_from).replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            pass
    if date_to:
        try:
            # Inclusive of the whole end day
            end = datetime.fromisoformat(date_to).replace(
                hour=23, minute=59, second=59, tzinfo=timezone.utc
            )
            date_filter["$lte"] = end
        except ValueError:
            pass
    if date_filter:
        query["created_at"] = date_filter

    total = await db.audit_logs.count_documents(query)
    raw = (
        await db.audit_logs.find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
        .to_list(length=limit)
    )

    actors = await _actor_names([entry.get("user_id") for entry in raw])

    logs = []
    for entry in raw:
        actor = actors.get(str(entry.get("user_id")), {})
        created = entry.get("created_at")
        logs.append({
            "id": str(entry["_id"]),
            "user_id": str(entry.get("user_id")) if entry.get("user_id") else None,
            "actor_name": actor.get("full_name"),
            "actor_role": actor.get("role"),
            "actor_email": actor.get("email"),
            "action": entry.get("action", ""),
            "resource_type": entry.get("resource_type", ""),
            "resource_id": entry.get("resource_id"),
            "details": entry.get("details") or {},
            "ip_address": entry.get("ip_address"),
            "created_at": created.isoformat() if isinstance(created, datetime) else None,
        })

    return {"logs": logs, "total": total, "limit": limit, "skip": skip}


async def get_audit_facets(hospital_id: str = None) -> dict:
    """Distinct actions and resource types, for populating filter dropdowns."""
    db = get_db()
    query: dict = {}

    if hospital_id is not None:
        member_ids = []
        async for user in db.users.find(
            {"hospital_id": to_object_id(hospital_id)}, {"_id": 1}
        ):
            member_ids.append(str(user["_id"]))
        if not member_ids:
            return {"actions": [], "resource_types": []}
        query["user_id"] = {"$in": member_ids}

    actions = await db.audit_logs.distinct("action", query)
    resource_types = await db.audit_logs.distinct("resource_type", query)

    return {
        "actions": sorted(a for a in actions if a),
        "resource_types": sorted(r for r in resource_types if r),
    }


# ── Response Models ──────────────────────────────────────────
# Shared by the platform and hospital audit endpoints.

class AuditLogEntry(BaseModel):
    id: str
    user_id: Optional[str] = None
    actor_name: Optional[str] = None
    actor_role: Optional[str] = None
    actor_email: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: dict = {}
    ip_address: Optional[str] = None
    created_at: Optional[str] = None


class AuditLogListResponse(BaseModel):
    logs: list[AuditLogEntry]
    total: int = Field(..., description="Matching entries before pagination")
    limit: int
    skip: int


class AuditFacetsResponse(BaseModel):
    actions: list[str] = []
    resource_types: list[str] = []
