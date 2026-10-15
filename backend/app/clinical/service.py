from datetime import datetime, timezone
from bson import ObjectId

from app.database import get_db
from app.common.models import serialize_doc, to_object_id
from app.common.exceptions import NotFoundError, ForbiddenError, BadRequestError
from app.common import patients as patient_data


# ── Access Control ───────────────────────────────────────────

async def resolve_patient_access(user: dict, patient_id: str) -> ObjectId:
    """Check who may read a patient's record; returns the patient's ID or raises 403/404."""
    db = get_db()
    role = user.get("role")
    patient_oid = to_object_id(patient_id)

    if role == "doctor":
        doctor = await db.users.find_one({"_id": to_object_id(user["id"])})
        if not doctor:
            raise NotFoundError("Doctor")
        assigned = [
            to_object_id(str(pid)) if isinstance(pid, str) else pid
            for pid in doctor.get("assigned_patients", [])
        ]
        if patient_oid not in assigned:
            raise ForbiddenError("This patient is not assigned to you")

    elif role == "patient":
        if patient_oid != to_object_id(user["id"]):
            raise ForbiddenError("You may only view your own record")

    elif role == "guardian":
        guardian = await db.users.find_one({"_id": to_object_id(user["id"])})
        linked = guardian.get("linked_patient_id") if guardian else None
        if not linked:
            raise ForbiddenError("No patient is linked to your guardian account")
        linked_oid = to_object_id(str(linked)) if isinstance(linked, str) else linked
        if patient_oid != linked_oid:
            raise ForbiddenError("You may only view your linked patient's record")

    elif role == "hospital":
        hospital_id = user.get("hospital_id")
        if not hospital_id:
            raise ForbiddenError("Your account is not linked to a hospital")
        in_hospital = await db.users.find_one({
            "_id": patient_oid,
            "hospital_id": to_object_id(str(hospital_id)),
            "role": "patient",
        })
        if not in_hospital:
            raise ForbiddenError("This patient does not belong to your hospital")

    else:
        raise ForbiddenError("Your role cannot view clinical records")

    patient = await db.users.find_one({"_id": patient_oid, "role": "patient"})
    if not patient:
        raise NotFoundError("Patient")

    return patient_oid


async def require_doctor_for_patient(user: dict, patient_id: str) -> ObjectId:
    """Writes to the clinical record are doctor-only. Returns the patient's ID."""
    if user.get("role") != "doctor":
        raise ForbiddenError("Only a doctor may modify the clinical record")
    return await resolve_patient_access(user, patient_id)


async def _user_names(oids: list[ObjectId]) -> dict[str, str]:
    """Batch-resolve user IDs to display names."""
    db = get_db()
    if not oids:
        return {}
    names = {}
    async for user in db.users.find({"_id": {"$in": oids}}, {"full_name": 1}):
        names[str(user["_id"])] = user.get("full_name", "")
    return names


# ── Medications ──────────────────────────────────────────────

async def list_medications(patient_oid: ObjectId) -> tuple[list[dict], int]:
    """List a patient's medications, active first. Returns (medications, active_count)."""
    db = get_db()
    raw = (
        await db.medications.find({"patient_id": patient_oid})
        .sort([("is_active", -1), ("created_at", -1)])
        .to_list(length=200)
    )

    doctor_oids = [
        m["doctor_id"] for m in raw
        if isinstance(m.get("doctor_id"), ObjectId)
    ]
    names = await _user_names(doctor_oids)

    medications = []
    for med in raw:
        doc = serialize_doc(med)
        doc["doctor_name"] = names.get(doc.get("doctor_id"))
        medications.append(doc)

    active = sum(1 for m in medications if m.get("is_active"))
    return medications, active


async def create_medication(
    patient_oid: ObjectId, doctor_id: str, data: dict
) -> dict:
    """Prescribe a medication for a patient."""
    db = get_db()
    now = datetime.now(timezone.utc)

    doc = {
        "patient_id": patient_oid,
        "doctor_id": to_object_id(doctor_id),
        "name": data["name"],
        "dosage": data["dosage"],
        "frequency": data["frequency"],
        "start_date": data.get("start_date"),
        "end_date": data.get("end_date"),
        "notes": data.get("notes"),
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }

    result = await db.medications.insert_one(doc)
    created = await db.medications.find_one({"_id": result.inserted_id})

    serialized = serialize_doc(created)
    names = await _user_names([to_object_id(doctor_id)])
    serialized["doctor_name"] = names.get(doctor_id)
    return serialized


async def update_medication(
    patient_oid: ObjectId, medication_id: str, data: dict
) -> dict:
    """Update or discontinue a medication belonging to this patient."""
    db = get_db()
    med_oid = to_object_id(medication_id)

    existing = await db.medications.find_one({
        "_id": med_oid,
        "patient_id": patient_oid,
    })
    if not existing:
        raise NotFoundError("Medication")

    updates = {k: v for k, v in data.items() if v is not None}
    if not updates:
        raise BadRequestError("No fields to update")

    updates["updated_at"] = datetime.now(timezone.utc)
    await db.medications.update_one({"_id": med_oid}, {"$set": updates})

    updated = await db.medications.find_one({"_id": med_oid})
    serialized = serialize_doc(updated)

    doctor_id = serialized.get("doctor_id")
    if doctor_id:
        names = await _user_names([to_object_id(doctor_id)])
        serialized["doctor_name"] = names.get(doctor_id)

    return serialized


# ── Vitals ───────────────────────────────────────────────────

async def list_vitals(patient_oid: ObjectId, limit: int = 50) -> list[dict]:
    """List a patient's recorded vitals, most recent first."""
    db = get_db()
    raw = (
        await db.vitals.find({"patient_id": patient_oid})
        .sort("recorded_at", -1)
        .to_list(length=limit)
    )

    recorder_oids = [
        v["recorded_by"] for v in raw
        if isinstance(v.get("recorded_by"), ObjectId)
    ]
    names = await _user_names(recorder_oids)

    vitals = []
    for entry in raw:
        doc = serialize_doc(entry)
        doc["recorded_by_name"] = names.get(doc.get("recorded_by"))
        vitals.append(doc)

    return vitals


async def create_vitals(
    patient_oid: ObjectId, recorded_by: str, data: dict
) -> dict:
    """Record a set of vital signs for a patient."""
    db = get_db()

    measurements = ("blood_pressure", "heart_rate", "temperature", "weight")
    if not any(data.get(field) is not None for field in measurements):
        raise BadRequestError("Record at least one measurement")

    now = datetime.now(timezone.utc)
    doc = {
        "patient_id": patient_oid,
        "recorded_by": to_object_id(recorded_by),
        "recorded_at": now,
        "blood_pressure": data.get("blood_pressure"),
        "heart_rate": data.get("heart_rate"),
        "temperature": data.get("temperature"),
        "weight": data.get("weight"),
        "notes": data.get("notes"),
    }

    result = await db.vitals.insert_one(doc)
    created = await db.vitals.find_one({"_id": result.inserted_id})

    serialized = serialize_doc(created)
    names = await _user_names([to_object_id(recorded_by)])
    serialized["recorded_by_name"] = names.get(recorded_by)
    return serialized


# ── Interventions ────────────────────────────────────────────

async def list_interventions(patient_oid: ObjectId) -> tuple[list[dict], int]:
    """List a patient's interventions, newest first. Returns (items, pending_count)."""
    db = get_db()
    raw = (
        await db.interventions.find({"patient_id": patient_oid})
        .sort("created_at", -1)
        .to_list(length=200)
    )
    return await _enrich_interventions(raw)


async def create_intervention(
    patient_oid: ObjectId, doctor_id: str, data: dict
) -> dict:
    """Record an intervention and mark its linked alert read."""
    db = get_db()
    doctor_oid = to_object_id(doctor_id)
    now = datetime.now(timezone.utc)

    alert_oid = None
    if data.get("alert_id"):
        alert_oid = to_object_id(data["alert_id"])
        alert = await db.alerts.find_one({
            "_id": alert_oid,
            "patient_id": patient_oid,
        })
        if not alert:
            raise NotFoundError("Alert for this patient")

    intervention_type = data["intervention_type"]
    doc = {
        "patient_id": patient_oid,
        "doctor_id": doctor_oid,
        "alert_id": alert_oid,
        "intervention_type": (
            intervention_type.value
            if hasattr(intervention_type, "value") else intervention_type
        ),
        "description": data["description"],
        "outcome": None,
        "outcome_status": "pending",
        "follow_up_date": data.get("follow_up_date"),
        "created_at": now,
        "updated_at": now,
    }

    result = await db.interventions.insert_one(doc)

    # Close the loop: the alert that prompted this has now been acted on
    if alert_oid is not None:
        await db.alerts.update_one(
            {"_id": alert_oid, "target_user_id": doctor_oid},
            {"$set": {"is_read": True}},
        )

    created = await db.interventions.find_one({"_id": result.inserted_id})
    enriched, _ = await _enrich_interventions([created])
    return enriched[0]


async def update_intervention(
    patient_oid: ObjectId, intervention_id: str, data: dict
) -> dict:
    """Update an intervention, typically to record its outcome."""
    db = get_db()
    oid = to_object_id(intervention_id)

    existing = await db.interventions.find_one({
        "_id": oid,
        "patient_id": patient_oid,
    })
    if not existing:
        raise NotFoundError("Intervention")

    updates = {}
    for field in ("description", "outcome", "follow_up_date"):
        if data.get(field) is not None:
            updates[field] = data[field]

    if data.get("outcome_status") is not None:
        status = data["outcome_status"]
        updates["outcome_status"] = (
            status.value if hasattr(status, "value") else status
        )

    if not updates:
        raise BadRequestError("No fields to update")

    updates["updated_at"] = datetime.now(timezone.utc)
    await db.interventions.update_one({"_id": oid}, {"$set": updates})

    updated = await db.interventions.find_one({"_id": oid})
    enriched, _ = await _enrich_interventions([updated])
    return enriched[0]


async def _enrich_interventions(items: list[dict]) -> tuple[list[dict], int]:
    """Attach doctor names and linked alert messages to intervention docs."""
    db = get_db()

    doctor_oids = [i["doctor_id"] for i in items if isinstance(i.get("doctor_id"), ObjectId)]
    names = await _user_names(doctor_oids)

    alert_oids = [i["alert_id"] for i in items if isinstance(i.get("alert_id"), ObjectId)]
    alert_messages: dict[str, str] = {}
    if alert_oids:
        async for alert in db.alerts.find({"_id": {"$in": alert_oids}}, {"message": 1}):
            alert_messages[str(alert["_id"])] = alert.get("message", "")

    out = []
    for item in items:
        doc = serialize_doc(item)
        doc["doctor_name"] = names.get(doc.get("doctor_id"))
        doc["alert_summary"] = alert_messages.get(doc.get("alert_id"))
        doc.setdefault("outcome_status", "pending")
        out.append(doc)

    pending = sum(1 for i in out if i.get("outcome_status") == "pending")
    return out, pending


# ── Treatment Plan ───────────────────────────────────────────

async def get_treatment_plan(patient_oid: ObjectId) -> dict:
    """Get the patient's current care plan plus every superseded version."""
    db = get_db()
    raw = (
        await db.treatment_plans.find({"patient_id": patient_oid})
        .sort("version", -1)
        .to_list(length=100)
    )

    doctor_oids = [p["doctor_id"] for p in raw if isinstance(p.get("doctor_id"), ObjectId)]
    names = await _user_names(doctor_oids)

    plans = []
    for plan in raw:
        doc = serialize_doc(plan)
        doc["doctor_name"] = names.get(doc.get("doctor_id"))
        doc.setdefault("focus_areas", [])
        plans.append(doc)

    current = next((p for p in plans if p.get("is_current")), None)
    history = [p for p in plans if not p.get("is_current")]

    return {
        "current": current,
        "history": history,
        "total_versions": len(plans),
    }


async def upsert_treatment_plan(
    patient_oid: ObjectId, doctor_id: str, data: dict
) -> dict:
    """Publish a new care plan version; the old one is kept as history."""
    db = get_db()
    now = datetime.now(timezone.utc)

    previous = await db.treatment_plans.find_one({
        "patient_id": patient_oid,
        "is_current": True,
    })
    next_version = (previous.get("version", 1) + 1) if previous else 1

    if previous:
        await db.treatment_plans.update_one(
            {"_id": previous["_id"]},
            {"$set": {"is_current": False, "superseded_at": now}},
        )

    doc = {
        "patient_id": patient_oid,
        "doctor_id": to_object_id(doctor_id),
        "summary": data["summary"],
        "focus_areas": data.get("focus_areas", []),
        "review_date": data.get("review_date"),
        "version": next_version,
        "is_current": True,
        "created_at": now,
        "superseded_at": None,
    }

    result = await db.treatment_plans.insert_one(doc)
    created = await db.treatment_plans.find_one({"_id": result.inserted_id})

    serialized = serialize_doc(created)
    names = await _user_names([to_object_id(doctor_id)])
    serialized["doctor_name"] = names.get(doctor_id)
    serialized.setdefault("focus_areas", [])
    return serialized


# ── Aggregated Medical History ───────────────────────────────

def _iso(value) -> str:
    """Coerce a stored timestamp into an ISO string for sorting and display."""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value) if value else ""


async def get_medical_history(patient_oid: ObjectId, limit: int = 100) -> dict:
    """Merge every clinical record type into one reverse-chronological feed."""
    db = get_db()

    patient = await db.users.find_one({"_id": patient_oid}, {"full_name": 1})
    profile = await patient_data.get_profile(patient_oid)

    events: list[dict] = []

    # Daily check-ins
    async for ci in db.daily_checkins.find({"patient_id": patient_oid}).sort("created_at", -1).limit(limit):
        events.append({
            "event_type": "checkin",
            "occurred_at": _iso(ci.get("created_at")),
            "title": f"Daily check-in — {ci.get('date', '')}",
            "summary": (
                f"Mood {ci.get('mood', '—')} · "
                f"Craving {ci.get('craving_level', '—')}/10 · "
                f"Stress {ci.get('stress_level', '—')}/10 · "
                f"Sleep {ci.get('sleep_hours', '—')}h"
            ),
            "detail": {
                "mood": ci.get("mood"),
                "craving_level": ci.get("craving_level"),
                "stress_level": ci.get("stress_level"),
                "sleep_hours": ci.get("sleep_hours"),
                "medication_taken": ci.get("medication_taken"),
                "physical_activity_minutes": ci.get("physical_activity_minutes"),
                "notes": ci.get("notes"),
            },
        })

    # Clinical notes
    async for note in db.clinical_notes.find({"patient_id": patient_oid}).sort("created_at", -1).limit(limit):
        events.append({
            "event_type": "note",
            "occurred_at": _iso(note.get("created_at")),
            "title": f"Clinical note ({note.get('note_type', 'progress')})",
            "summary": (note.get("content") or "")[:200],
            "detail": {
                "doctor_name": note.get("doctor_name"),
                "note_type": note.get("note_type"),
                "content": note.get("content"),
            },
        })

    # Recovery goals
    async for goal in db.recovery_goals.find({"patient_id": patient_oid}).sort("created_at", -1).limit(limit):
        events.append({
            "event_type": "goal",
            "occurred_at": _iso(goal.get("created_at")),
            "title": f"Recovery goal — {goal.get('title', '')}",
            "summary": f"Status: {goal.get('status', 'not_started')}",
            "detail": {
                "status": goal.get("status"),
                "target_date": goal.get("target_date"),
                "description": goal.get("description"),
            },
        })

    # Medications
    async for med in db.medications.find({"patient_id": patient_oid}).sort("created_at", -1).limit(limit):
        events.append({
            "event_type": "medication",
            "occurred_at": _iso(med.get("created_at")),
            "title": f"Medication — {med.get('name', '')}",
            "summary": f"{med.get('dosage', '')} · {med.get('frequency', '')}"
                       + ("" if med.get("is_active", True) else " · discontinued"),
            "detail": {
                "dosage": med.get("dosage"),
                "frequency": med.get("frequency"),
                "is_active": med.get("is_active", True),
                "notes": med.get("notes"),
            },
        })

    # Vitals
    async for v in db.vitals.find({"patient_id": patient_oid}).sort("recorded_at", -1).limit(limit):
        parts = []
        if v.get("blood_pressure"):
            parts.append(f"BP {v['blood_pressure']}")
        if v.get("heart_rate"):
            parts.append(f"HR {v['heart_rate']}bpm")
        if v.get("temperature"):
            parts.append(f"Temp {v['temperature']}°C")
        if v.get("weight"):
            parts.append(f"Weight {v['weight']}kg")
        events.append({
            "event_type": "vitals",
            "occurred_at": _iso(v.get("recorded_at")),
            "title": "Vitals recorded",
            "summary": " · ".join(parts) or "—",
            "detail": {
                "blood_pressure": v.get("blood_pressure"),
                "heart_rate": v.get("heart_rate"),
                "temperature": v.get("temperature"),
                "weight": v.get("weight"),
                "notes": v.get("notes"),
            },
        })

    # Interventions
    async for iv in db.interventions.find({"patient_id": patient_oid}).sort("created_at", -1).limit(limit):
        label = (iv.get("intervention_type") or "other").replace("_", " ")
        status = iv.get("outcome_status", "pending")
        events.append({
            "event_type": "intervention",
            "occurred_at": _iso(iv.get("created_at")),
            "title": f"Intervention — {label}",
            "summary": (iv.get("description") or "")[:200]
                       + (f" · outcome: {status}" if status != "pending" else " · outcome pending"),
            "detail": {
                "intervention_type": iv.get("intervention_type"),
                "description": iv.get("description"),
                "outcome": iv.get("outcome"),
                "outcome_status": status,
                "follow_up_date": iv.get("follow_up_date"),
            },
        })

    # Care plan revisions
    async for plan in db.treatment_plans.find({"patient_id": patient_oid}).sort("version", -1).limit(limit):
        events.append({
            "event_type": "care_plan",
            "occurred_at": _iso(plan.get("created_at")),
            "title": f"Care plan v{plan.get('version', 1)}"
                     + ("" if plan.get("is_current") else " (superseded)"),
            "summary": (plan.get("summary") or "")[:200],
            "detail": {
                "version": plan.get("version"),
                "is_current": plan.get("is_current", False),
                "focus_areas": plan.get("focus_areas", []),
                "review_date": plan.get("review_date"),
            },
        })

    # Appointments
    async for appt in db.appointments.find({"patient_id": patient_oid}).sort("date_time", -1).limit(limit):
        events.append({
            "event_type": "appointment",
            "occurred_at": _iso(appt.get("date_time")),
            "title": f"Appointment — {appt.get('reason', 'Consultation')}",
            "summary": f"Status: {appt.get('status', 'scheduled')}",
            "detail": {
                "status": appt.get("status"),
                "duration_minutes": appt.get("duration_minutes"),
                "notes": appt.get("notes"),
            },
        })

    events.sort(key=lambda e: e["occurred_at"], reverse=True)
    events = events[:limit]

    return {
        "patient_id": str(patient_oid),
        "patient_name": patient.get("full_name", "Patient") if patient else "Patient",
        "profile": profile,
        "events": events,
        "total": len(events),
    }
