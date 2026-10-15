from datetime import datetime, timezone

from app.database import get_db
from app.common.models import serialize_doc, to_object_id
from app.common.exceptions import NotFoundError, ConflictError
from app.common import alerts as alert_engine
from app.common import patients as patient_data


# ── Dashboard ────────────────────────────────────────────────

async def get_patient_dashboard(patient_id: str) -> dict:
    """Build dashboard data: today's check-in status, streak, goals, care team."""
    db = get_db()
    patient_oid = to_object_id(patient_id)

    patient = await db.users.find_one({"_id": patient_oid})
    if not patient:
        raise NotFoundError("Patient")

    today = patient_data.today_utc()

    today_checkin = await db.daily_checkins.find_one({
        "patient_id": patient_oid,
        "date": today,
    })

    streak = await patient_data.calculate_streak(patient_oid)

    active_goals = await db.recovery_goals.count_documents({
        "patient_id": patient_oid,
        "status": {"$in": ["not_started", "in_progress"]},
    })
    total_goals = await db.recovery_goals.count_documents({
        "patient_id": patient_oid,
    })

    recent_goals_cursor = db.recovery_goals.find(
        {"patient_id": patient_oid}
    ).sort("created_at", -1).limit(5)
    recent_goals = []
    async for goal in recent_goals_cursor:
        doc = serialize_doc(goal)
        recent_goals.append({
            "id": doc["id"],
            "title": doc.get("title", ""),
            "status": doc.get("status", "not_started"),
            "target_date": doc.get("target_date"),
        })

    care_team = await patient_data.get_care_team(patient_oid)

    # Clinical profile drives the abstinence counter
    profile = await patient_data.get_profile(patient_oid)

    return {
        "full_name": patient.get("full_name", "Patient"),
        "today_checkin_done": today_checkin is not None,
        "streak_days": streak,
        "abstinence_days": profile.get("abstinence_days"),
        "sobriety_date": profile.get("sobriety_date"),
        "active_goals": active_goals,
        "total_goals": total_goals,
        "care_team": care_team,
        "recent_goals": recent_goals,
    }


# ── Check-in Submission ──────────────────────────────────────

async def submit_checkin(patient_id: str, data: dict) -> dict:
    """Create a daily check-in. Rejects duplicates for the same date."""
    db = get_db()
    patient_oid = to_object_id(patient_id)
    now = datetime.now(timezone.utc)
    today = patient_data.today_utc()

    existing = await db.daily_checkins.find_one({
        "patient_id": patient_oid,
        "date": today,
    })
    if existing:
        raise ConflictError("You have already submitted a check-in for today")

    checkin_doc = {
        "patient_id": patient_oid,
        "date": today,
        "mood": data["mood"],
        "stress_level": data["stress_level"],
        "sleep_hours": data["sleep_hours"],
        "craving_level": data["craving_level"],
        "medication_taken": data["medication_taken"],
        "physical_activity_minutes": data.get("physical_activity_minutes", 0),
        "notes": data.get("notes"),
        "created_at": now,
    }

    result = await db.daily_checkins.insert_one(checkin_doc)
    created = await db.daily_checkins.find_one({"_id": result.inserted_id})
    doc = serialize_doc(created)
    doc["patient_id"] = patient_id

    # Run the clinical alert engine over the submitted values
    await alert_engine.evaluate_checkin(patient_oid, checkin_doc)

    return doc


# ── Check-in History ─────────────────────────────────────────

async def get_checkin_history(patient_id: str, limit: int = 30) -> list[dict]:
    """Get patient's historical check-ins sorted by date descending."""
    db = get_db()
    patient_oid = to_object_id(patient_id)

    checkins = (
        await db.daily_checkins.find({"patient_id": patient_oid})
        .sort("date", -1)
        .to_list(length=limit)
    )

    result = []
    for checkin in checkins:
        doc = serialize_doc(checkin)
        doc["patient_id"] = patient_id
        if isinstance(doc.get("date"), datetime):
            doc["date"] = doc["date"].isoformat()
        result.append(doc)

    return result


# ── Recovery Goals ───────────────────────────────────────────

async def get_patient_goals(patient_id: str) -> list[dict]:
    """Get patient's recovery goals."""
    db = get_db()
    patient_oid = to_object_id(patient_id)

    goals = (
        await db.recovery_goals.find({"patient_id": patient_oid})
        .sort("created_at", -1)
        .to_list(length=100)
    )

    result = []
    for goal in goals:
        doc = serialize_doc(goal)
        doc["patient_id"] = patient_id
        result.append({
            "id": doc["id"],
            "title": doc.get("title", ""),
            "status": doc.get("status", "not_started"),
            "target_date": doc.get("target_date"),
        })

    return result


# ── Patient Profile ──────────────────────────────────────────

async def get_patient_profile(patient_id: str) -> dict:
    """Get patient profile with medical info and care team."""
    db = get_db()
    patient_oid = to_object_id(patient_id)

    patient = await db.users.find_one({"_id": patient_oid})
    if not patient:
        raise NotFoundError("Patient")

    doc = serialize_doc(patient)

    # Clinical profile (behavioural recovery fields + abstinence counter)
    doc.update(await patient_data.get_profile(patient_oid))

    assigned_doctor = await db.users.find_one({
        "role": "doctor",
        "assigned_patients": patient_oid,
        "is_active": True,
    })
    if assigned_doctor:
        doc["assigned_doctor"] = {
            "id": str(assigned_doctor["_id"]),
            "full_name": assigned_doctor.get("full_name", "Doctor"),
            "role": "doctor",
            "email": assigned_doctor.get("email"),
            "phone": assigned_doctor.get("phone"),
        }
    else:
        doc["assigned_doctor"] = None

    guardian = await db.users.find_one({
        "role": "guardian",
        "linked_patient_id": patient_oid,
        "is_active": True,
    })
    if guardian:
        doc["guardian"] = {
            "id": str(guardian["_id"]),
            "full_name": guardian.get("full_name", "Guardian"),
            "role": "guardian",
            "email": guardian.get("email"),
            "phone": guardian.get("phone"),
        }
    else:
        doc["guardian"] = None

    return doc
