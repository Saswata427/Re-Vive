from datetime import datetime, timezone
from bson import ObjectId

from app.database import get_db
from app.common.models import serialize_doc, to_object_id
from app.common.exceptions import NotFoundError, ForbiddenError, BadRequestError
from app.common import alerts as alert_engine


# ── Helpers ──────────────────────────────────────────────────

def _as_oid(value) -> ObjectId:
    """Normalize a value that may be stored as either ObjectId or string."""
    if isinstance(value, ObjectId):
        return value
    return to_object_id(str(value))


async def _verify_assignment(doctor_id: str, patient_id: str) -> dict:
    """Verify the patient is assigned to this doctor. Returns the patient doc."""
    db = get_db()
    doctor = await db.users.find_one({"_id": to_object_id(doctor_id)})
    if not doctor:
        raise NotFoundError("Doctor")

    patient_oid = to_object_id(patient_id)
    assigned_oids = [_as_oid(pid) for pid in doctor.get("assigned_patients", [])]

    if patient_oid not in assigned_oids:
        raise ForbiddenError("This patient is not assigned to you")

    patient = await db.users.find_one({"_id": patient_oid, "role": "patient"})
    if not patient:
        raise NotFoundError("Patient")

    return patient


async def _enrich(appointments: list[dict]) -> list[dict]:
    """Attach patient_name and doctor_name to serialized appointment docs."""
    db = get_db()
    if not appointments:
        return []

    user_oids = []
    for appt in appointments:
        for key in ("patient_id", "doctor_id"):
            value = appt.get(key)
            if isinstance(value, ObjectId) and value not in user_oids:
                user_oids.append(value)

    names: dict[str, str] = {}
    if user_oids:
        cursor = db.users.find({"_id": {"$in": user_oids}}, {"full_name": 1})
        async for user in cursor:
            names[str(user["_id"])] = user.get("full_name", "")

    result = []
    for appt in appointments:
        doc = serialize_doc(appt)
        doc["patient_name"] = names.get(doc.get("patient_id"))
        doc["doctor_name"] = names.get(doc.get("doctor_id"))
        doc.setdefault("duration_minutes", 30)
        doc.setdefault("reason", "Consultation")
        result.append(doc)

    return result


async def _resolve_scope(user: dict) -> dict:
    """Build the Mongo filter that limits appointments to what a role may see."""
    db = get_db()
    role = user.get("role")
    user_oid = to_object_id(user["id"])

    if role == "doctor":
        return {"doctor_id": user_oid}

    if role == "patient":
        return {"patient_id": user_oid}

    if role == "guardian":
        guardian = await db.users.find_one({"_id": user_oid})
        linked = guardian.get("linked_patient_id") if guardian else None
        if not linked:
            raise ForbiddenError("No patient is linked to your guardian account")
        return {"patient_id": _as_oid(linked)}

    if role == "hospital":
        hospital_id = user.get("hospital_id")
        if not hospital_id:
            raise ForbiddenError("Your account is not linked to a hospital")
        return {"hospital_id": _as_oid(hospital_id)}

    if role == "admin":
        return {}

    raise ForbiddenError("Your role cannot view appointments")


# ── Listing ──────────────────────────────────────────────────

async def list_appointments(
    user: dict,
    status_filter: str = None,
    upcoming_only: bool = False,
    limit: int = 100,
) -> tuple[list[dict], int]:
    """List appointments visible to a user. Returns (appointments, upcoming_count)."""
    db = get_db()
    query = await _resolve_scope(user)

    if status_filter:
        query["status"] = status_filter

    now = datetime.now(timezone.utc)
    if upcoming_only:
        query["date_time"] = {"$gte": now}
        query.setdefault("status", "scheduled")

    raw = (
        await db.appointments.find(query)
        .sort("date_time", 1 if upcoming_only else -1)
        .to_list(length=limit)
    )

    # Count still-upcoming scheduled appointments within the same scope
    upcoming_query = await _resolve_scope(user)
    upcoming_query["status"] = "scheduled"
    upcoming_query["date_time"] = {"$gte": now}
    upcoming = await db.appointments.count_documents(upcoming_query)

    return await _enrich(raw), upcoming


async def get_appointment(user: dict, appointment_id: str) -> dict:
    """Fetch a single appointment the user is allowed to see."""
    db = get_db()
    query = await _resolve_scope(user)
    query["_id"] = to_object_id(appointment_id)

    appt = await db.appointments.find_one(query)
    if not appt:
        raise NotFoundError("Appointment")

    enriched = await _enrich([appt])
    return enriched[0]


# ── Creation ─────────────────────────────────────────────────

async def create_appointment(doctor_id: str, data: dict) -> dict:
    """Schedule an appointment for one of the doctor's assigned patients."""
    db = get_db()
    patient = await _verify_assignment(doctor_id, data["patient_id"])

    date_time = data["date_time"]
    if date_time.tzinfo is None:
        date_time = date_time.replace(tzinfo=timezone.utc)
    if date_time < datetime.now(timezone.utc):
        raise BadRequestError("Appointment time must be in the future")

    doctor = await db.users.find_one({"_id": to_object_id(doctor_id)})
    hospital_id = doctor.get("hospital_id") if doctor else None

    now = datetime.now(timezone.utc)
    appointment_doc = {
        "patient_id": patient["_id"],
        "doctor_id": to_object_id(doctor_id),
        "hospital_id": _as_oid(hospital_id) if hospital_id else None,
        "date_time": date_time,
        "duration_minutes": data.get("duration_minutes", 30),
        "reason": data["reason"],
        "status": "scheduled",
        "notes": data.get("notes"),
        "created_at": now,
        "updated_at": now,
    }

    result = await db.appointments.insert_one(appointment_doc)
    created = await db.appointments.find_one({"_id": result.inserted_id})

    # Notify the patient and their guardian
    doctor_name = doctor.get("full_name", "your doctor") if doctor else "your doctor"
    await alert_engine.broadcast_alert(
        patient["_id"],
        alert_engine.ALERT_APPOINTMENT,
        alert_engine.SEVERITY_LOW,
        f"Appointment with {doctor_name} scheduled for "
        f"{date_time.strftime('%d %b %Y at %H:%M')} — {data['reason']}",
        extra_recipients=[patient["_id"]],
    )

    enriched = await _enrich([created])
    return enriched[0]


# ── Updates ──────────────────────────────────────────────────

async def update_appointment(user: dict, appointment_id: str, data: dict) -> dict:
    """Update an appointment; patients and guardians may only cancel."""
    db = get_db()
    role = user.get("role")
    user_oid = to_object_id(user["id"])
    appt_oid = to_object_id(appointment_id)

    appt = await db.appointments.find_one({"_id": appt_oid})
    if not appt:
        raise NotFoundError("Appointment")

    # Normalize the status enum to its string value up front
    if data.get("status") is not None:
        status = data["status"]
        data["status"] = status.value if hasattr(status, "value") else status

    if role == "doctor":
        if _as_oid(appt["doctor_id"]) != user_oid:
            raise ForbiddenError("This appointment does not belong to you")
    elif role == "hospital":
        hospital_id = user.get("hospital_id")
        appt_hospital = appt.get("hospital_id")
        if not hospital_id or not appt_hospital or _as_oid(appt_hospital) != _as_oid(hospital_id):
            raise ForbiddenError("This appointment does not belong to your hospital")
    elif role in ("patient", "guardian"):
        scope = await _resolve_scope(user)
        if _as_oid(appt["patient_id"]) != scope["patient_id"]:
            raise ForbiddenError("This appointment does not belong to you")
        if set(data.keys()) - {"status"} or data.get("status") != "cancelled":
            raise ForbiddenError("You may only cancel this appointment")
    else:
        raise ForbiddenError("Your role cannot modify appointments")

    # Completed and cancelled are terminal — schedule a new appointment instead
    if appt.get("status") in ("completed", "cancelled"):
        raise BadRequestError(
            f"Appointment is already {appt['status']} and can no longer be changed"
        )

    updates: dict = {}
    for field in ("duration_minutes", "reason", "notes"):
        if field in data and data[field] is not None:
            updates[field] = data[field]

    if data.get("status") is not None:
        updates["status"] = data["status"]

    rescheduled = False
    if data.get("date_time") is not None:
        date_time = data["date_time"]
        if date_time.tzinfo is None:
            date_time = date_time.replace(tzinfo=timezone.utc)
        if date_time < datetime.now(timezone.utc):
            raise BadRequestError("Appointment time must be in the future")
        updates["date_time"] = date_time
        rescheduled = True

    if not updates:
        raise BadRequestError("No fields to update")

    updates["updated_at"] = datetime.now(timezone.utc)
    await db.appointments.update_one({"_id": appt_oid}, {"$set": updates})

    updated = await db.appointments.find_one({"_id": appt_oid})
    patient_oid = _as_oid(updated["patient_id"])

    # Notify the care team about reschedules and cancellations
    if rescheduled:
        await alert_engine.broadcast_alert(
            patient_oid,
            alert_engine.ALERT_APPOINTMENT,
            alert_engine.SEVERITY_LOW,
            f"Appointment rescheduled to "
            f"{updates['date_time'].strftime('%d %b %Y at %H:%M')}",
            extra_recipients=[patient_oid],
        )
    elif updates.get("status") == "cancelled":
        await alert_engine.broadcast_alert(
            patient_oid,
            alert_engine.ALERT_APPOINTMENT,
            alert_engine.SEVERITY_MEDIUM,
            f"Appointment on "
            f"{_as_datetime(updated['date_time']).strftime('%d %b %Y at %H:%M')} "
            f"was cancelled",
            extra_recipients=[patient_oid],
        )

    enriched = await _enrich([updated])
    return enriched[0]


def _as_datetime(value) -> datetime:
    """Coerce a stored date_time value into a datetime for formatting."""
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))
