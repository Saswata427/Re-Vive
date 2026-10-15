"""Patient helpers: clinical profile, abstinence days, streak and care team."""

from datetime import datetime, timezone, timedelta, date
from typing import Optional
from bson import ObjectId

from app.database import get_db


# ── Clinical Profile ─────────────────────────────────────────

# Fields a hospital admin or doctor may set on a patient's clinical profile
PROFILE_FIELDS = (
    "primary_condition",
    "program_start_date",
    "sobriety_date",
    "therapy_program",
    "emergency_contact",
    "medical_notes",
)

# Empty profile shape, so responses are consistent when no record exists yet
EMPTY_PROFILE = {field: None for field in PROFILE_FIELDS}


def _to_date_str(value) -> Optional[str]:
    """Normalize a stored date (datetime, date, or string) to YYYY-MM-DD."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    return str(value)


def calculate_abstinence_days(sobriety_date) -> Optional[int]:
    """Days since the sobriety date; None if unset, 0 if it's in the future."""
    parsed = _to_date_str(sobriety_date)
    if not parsed:
        return None

    try:
        start = datetime.strptime(parsed[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None

    delta = (datetime.now(timezone.utc).date() - start).days
    return max(0, delta)


async def get_profile(patient_oid: ObjectId) -> dict:
    """A patient's clinical profile with every field present."""
    db = get_db()
    profile = await db.patient_profiles.find_one({"user_id": patient_oid})

    result = dict(EMPTY_PROFILE)
    if profile:
        for field in PROFILE_FIELDS:
            value = profile.get(field)
            if field.endswith("_date"):
                value = _to_date_str(value)
            result[field] = value

    result["abstinence_days"] = calculate_abstinence_days(result.get("sobriety_date"))
    return result


async def upsert_profile(patient_oid: ObjectId, data: dict, updated_by: str) -> dict:
    """Create or update a clinical profile; fields not sent are left alone."""
    db = get_db()

    updates = {}
    for field in PROFILE_FIELDS:
        if data.get(field) is not None:
            value = data[field]
            updates[field] = _to_date_str(value) if field.endswith("_date") else value

    now = datetime.now(timezone.utc)
    updates["updated_at"] = now
    updates["updated_by"] = updated_by

    await db.patient_profiles.update_one(
        {"user_id": patient_oid},
        {
            "$set": updates,
            "$setOnInsert": {"user_id": patient_oid, "created_at": now},
        },
        upsert=True,
    )

    return await get_profile(patient_oid)


# ── Streak and Care Team ─────────────────────────────────────

def today_utc() -> str:
    """Today's date as YYYY-MM-DD in UTC, the calendar check-ins are filed under."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


async def calculate_streak(patient_oid: ObjectId) -> int:
    """Check-in streak ending today or yesterday, counted in UTC."""
    db = get_db()

    # The last 60 check-ins bound the longest streak this needs to see
    checkins = (
        await db.daily_checkins.find(
            {"patient_id": patient_oid},
            {"date": 1}
        ).sort("date", -1).to_list(length=60)
    )

    checkin_dates = set()
    for ci in checkins:
        d = ci.get("date")
        if isinstance(d, str):
            checkin_dates.add(d)
        elif isinstance(d, datetime):
            checkin_dates.add(d.strftime("%Y-%m-%d"))

    if not checkin_dates:
        return 0

    today = datetime.now(timezone.utc).date()
    check_date = today
    # Today's check-in may simply not be done yet; the streak is still alive
    if today.strftime("%Y-%m-%d") not in checkin_dates:
        check_date = today - timedelta(days=1)

    streak = 0
    while check_date.strftime("%Y-%m-%d") in checkin_dates:
        streak += 1
        check_date -= timedelta(days=1)

    return streak


async def get_care_team(patient_oid: ObjectId) -> list[dict]:
    """The patient's active assigned doctors, then their guardian."""
    db = get_db()
    team = []

    doctor_cursor = db.users.find({
        "role": "doctor",
        "assigned_patients": patient_oid,
        "is_active": True,
    })
    async for doc in doctor_cursor:
        team.append({
            "id": str(doc["_id"]),
            "full_name": doc.get("full_name", "Doctor"),
            "role": "doctor",
            "email": doc.get("email"),
            "phone": doc.get("phone"),
        })

    guardian = await db.users.find_one({
        "role": "guardian",
        "linked_patient_id": patient_oid,
        "is_active": True,
    })
    if guardian:
        team.append({
            "id": str(guardian["_id"]),
            "full_name": guardian.get("full_name", "Guardian"),
            "role": "guardian",
            "email": guardian.get("email"),
            "phone": guardian.get("phone"),
        })

    return team
