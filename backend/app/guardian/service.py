from datetime import datetime

from app.database import get_db
from app.common.models import serialize_doc, to_object_id
from app.common.exceptions import NotFoundError, ForbiddenError
from app.common import patients as patient_data
from app.common import recovery


# ── Helpers ──────────────────────────────────────────────────

async def _get_linked_patient(guardian_id: str) -> dict:
    """The guardian and their linked patient, or raise if either is missing."""
    db = get_db()
    guardian_oid = to_object_id(guardian_id)

    guardian = await db.users.find_one({"_id": guardian_oid})
    if not guardian:
        raise NotFoundError("Guardian")

    linked_id = guardian.get("linked_patient_id")
    if not linked_id:
        raise ForbiddenError("No patient is linked to your guardian account")

    # linked_patient_id may be stored as ObjectId or string
    if isinstance(linked_id, str):
        linked_id = to_object_id(linked_id)

    patient = await db.users.find_one({"_id": linked_id, "role": "patient"})
    if not patient:
        raise NotFoundError("Linked patient")

    return guardian, patient


# ── Dashboard ────────────────────────────────────────────────

async def get_guardian_dashboard(guardian_id: str) -> dict:
    """Build guardian dashboard: linked patient summary, latest vitals, alerts."""
    db = get_db()
    guardian, patient = await _get_linked_patient(guardian_id)
    patient_oid = patient["_id"]
    today = patient_data.today_utc()

    today_checkin = await db.daily_checkins.find_one({
        "patient_id": patient_oid,
        "date": today,
    })

    # Latest check-in for pain/mood preview
    latest_checkin = await db.daily_checkins.find_one(
        {"patient_id": patient_oid},
        sort=[("date", -1)]
    )

    streak = await patient_data.calculate_streak(patient_oid)

    active_goals = await db.recovery_goals.count_documents({
        "patient_id": patient_oid,
        "status": {"$in": ["not_started", "in_progress"]},
    })
    total_goals = await db.recovery_goals.count_documents({
        "patient_id": patient_oid,
    })

    # Unread alerts for this guardian
    guardian_oid = to_object_id(guardian_id)
    unread_alerts = await db.alerts.count_documents({
        "target_user_id": guardian_oid,
        "is_read": False,
    })

    profile = await patient_data.get_profile(patient_oid)

    # Recovery score (headline figure only — the full breakdown is clinical)
    score = await recovery.calculate_recovery_score(patient_oid)

    care_team = await patient_data.get_care_team(patient_oid)

    return {
        "recovery_score": score.get("score"),
        "recovery_band": score.get("band"),
        "recovery_label": score.get("label"),
        "recovery_trend": score.get("trend"),
        "guardian_name": guardian.get("full_name", "Guardian"),
        "patient_name": patient.get("full_name", "Patient"),
        "patient_id": str(patient_oid),
        "primary_condition": profile.get("primary_condition"),
        "today_checkin_done": today_checkin is not None,
        "latest_craving_level": latest_checkin.get("craving_level") if latest_checkin else None,
        "latest_stress_level": latest_checkin.get("stress_level") if latest_checkin else None,
        "latest_mood": latest_checkin.get("mood") if latest_checkin else None,
        "streak_days": streak,
        "abstinence_days": profile.get("abstinence_days"),
        "sobriety_date": profile.get("sobriety_date"),
        "active_goals": active_goals,
        "total_goals": total_goals,
        "unread_alerts": unread_alerts,
        "care_team": care_team,
    }


# ── Patient Overview ─────────────────────────────────────────

async def get_patient_overview(guardian_id: str) -> dict:
    """Get detailed read-only view of the linked patient's recovery data."""
    db = get_db()
    guardian, patient = await _get_linked_patient(guardian_id)
    patient_oid = patient["_id"]


    # Clinical profile (behavioural recovery fields + abstinence counter)
    profile = await patient_data.get_profile(patient_oid)

    # Recent check-ins (last 14)
    checkins_raw = (
        await db.daily_checkins.find({"patient_id": patient_oid})
        .sort("date", -1)
        .to_list(length=14)
    )
    recent_checkins = []
    for ci in checkins_raw:
        doc = serialize_doc(ci)
        doc["patient_id"] = str(patient_oid)
        if isinstance(doc.get("date"), datetime):
            doc["date"] = doc["date"].isoformat()
        recent_checkins.append(doc)

    goals_raw = (
        await db.recovery_goals.find({"patient_id": patient_oid})
        .sort("created_at", -1)
        .to_list(length=100)
    )
    goals = []
    for goal in goals_raw:
        doc = serialize_doc(goal)
        goals.append({
            "id": doc["id"],
            "title": doc.get("title", ""),
            "status": doc.get("status", "not_started"),
            "target_date": doc.get("target_date"),
        })

    care_team = await patient_data.get_care_team(patient_oid)

    return {
        "patient_id": str(patient_oid),
        "patient_name": patient.get("full_name", "Patient"),
        "email": patient.get("email"),
        "phone": patient.get("phone"),
        "primary_condition": profile.get("primary_condition"),
        "program_start_date": profile.get("program_start_date"),
        "sobriety_date": profile.get("sobriety_date"),
        "therapy_program": profile.get("therapy_program"),
        "medical_notes": profile.get("medical_notes"),
        "abstinence_days": profile.get("abstinence_days"),
        "recent_checkins": recent_checkins,
        "goals": goals,
        "care_team": care_team,
    }
