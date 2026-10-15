from datetime import datetime, timezone, timedelta

from app.database import get_db
from app.common.models import serialize_doc, to_object_id
from app.common.exceptions import NotFoundError, ForbiddenError, BadRequestError
from app.common import patients as patient_data


# ── Helpers ──────────────────────────────────────────────────

async def _verify_assignment(doctor_id: str, patient_id: str) -> dict:
    """Verify that the patient is assigned to this doctor. Returns the patient doc."""
    db = get_db()
    doctor = await db.users.find_one({"_id": to_object_id(doctor_id)})
    if not doctor:
        raise NotFoundError("Doctor")

    patient_oid = to_object_id(patient_id)
    assigned = doctor.get("assigned_patients", [])

    # Normalize to ObjectId for comparison
    assigned_oids = [
        to_object_id(str(pid)) if isinstance(pid, str) else pid
        for pid in assigned
    ]

    if patient_oid not in assigned_oids:
        raise ForbiddenError("This patient is not assigned to you")

    patient = await db.users.find_one({"_id": patient_oid, "role": "patient"})
    if not patient:
        raise NotFoundError("Patient")

    return patient


# ── Dashboard Stats ──────────────────────────────────────────

async def get_doctor_dashboard_stats(doctor_id: str) -> dict:
    """Get dashboard statistics for a doctor."""
    db = get_db()
    doctor = await db.users.find_one({"_id": to_object_id(doctor_id)})
    if not doctor:
        raise NotFoundError("Doctor")

    assigned = doctor.get("assigned_patients", [])
    assigned_count = len(assigned)

    # Count check-ins in last 7 days across all assigned patients
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent_checkins = 0
    if assigned:
        recent_checkins = await db.daily_checkins.count_documents({
            "patient_id": {"$in": [to_object_id(str(pid)) for pid in assigned]},
            "created_at": {"$gte": seven_days_ago},
        })

    active_goals = 0
    if assigned:
        active_goals = await db.recovery_goals.count_documents({
            "patient_id": {"$in": [to_object_id(str(pid)) for pid in assigned]},
            "status": {"$in": ["not_started", "in_progress"]},
        })

    total_notes = await db.clinical_notes.count_documents({
        "doctor_id": to_object_id(doctor_id),
    })

    return {
        "assigned_patients": assigned_count,
        "recent_checkins": recent_checkins,
        "active_goals": active_goals,
        "total_notes": total_notes,
    }


# ── Patient List ─────────────────────────────────────────────

async def get_assigned_patients(doctor_id: str) -> list[dict]:
    """Get all patients assigned to this doctor with summary info."""
    db = get_db()
    doctor = await db.users.find_one({"_id": to_object_id(doctor_id)})
    if not doctor:
        raise NotFoundError("Doctor")

    assigned = doctor.get("assigned_patients", [])
    if not assigned:
        return []

    patients = []
    for pid in assigned:
        patient_oid = to_object_id(str(pid)) if isinstance(pid, str) else pid
        patient = await db.users.find_one({"_id": patient_oid, "role": "patient"})
        if not patient:
            continue

        doc = serialize_doc(patient)

        last_checkin = await db.daily_checkins.find_one(
            {"patient_id": patient_oid},
            sort=[("date", -1)],
        )
        doc["last_checkin_date"] = (
            last_checkin["date"] if last_checkin and "date" in last_checkin else None
        )
        if isinstance(doc["last_checkin_date"], datetime):
            doc["last_checkin_date"] = doc["last_checkin_date"].isoformat()

        doc["active_goals"] = await db.recovery_goals.count_documents({
            "patient_id": patient_oid,
            "status": {"$in": ["not_started", "in_progress"]},
        })

        patients.append(doc)

    return patients


# ── Patient Detail ───────────────────────────────────────────

async def get_patient_detail(doctor_id: str, patient_id: str) -> dict:
    """Get detailed patient info including profile data."""
    patient = await _verify_assignment(doctor_id, patient_id)
    db = get_db()
    patient_oid = to_object_id(patient_id)

    doc = serialize_doc(patient)

    # Clinical profile (behavioural recovery fields + abstinence counter)
    doc.update(await patient_data.get_profile(patient_oid))

    doc["total_checkins"] = await db.daily_checkins.count_documents(
        {"patient_id": patient_oid}
    )
    doc["total_notes"] = await db.clinical_notes.count_documents(
        {"patient_id": patient_oid}
    )
    doc["total_goals"] = await db.recovery_goals.count_documents(
        {"patient_id": patient_oid}
    )

    return doc


# ── Clinical Profile ─────────────────────────────────────────

async def get_patient_profile(doctor_id: str, patient_id: str) -> dict:
    """Get an assigned patient's clinical profile."""
    await _verify_assignment(doctor_id, patient_id)
    return await patient_data.get_profile(to_object_id(patient_id))


async def update_patient_profile(
    doctor_id: str, patient_id: str, data: dict
) -> dict:
    """Create or update an assigned patient's clinical profile."""
    await _verify_assignment(doctor_id, patient_id)

    if not any(data.get(field) is not None for field in patient_data.PROFILE_FIELDS):
        raise BadRequestError("No profile fields to update")

    return await patient_data.upsert_profile(
        to_object_id(patient_id), data, updated_by=doctor_id
    )


# ── Caseload Analytics ───────────────────────────────────────

async def get_caseload_analytics(doctor_id: str) -> dict:
    """The doctor's whole caseload at a glance, for triage."""
    from app.common import recovery

    db = get_db()
    doctor = await db.users.find_one({"_id": to_object_id(doctor_id)})
    if not doctor:
        raise NotFoundError("Doctor")

    assigned = [
        to_object_id(str(pid)) if isinstance(pid, str) else pid
        for pid in doctor.get("assigned_patients", [])
    ]

    if not assigned:
        return {
            "total_patients": 0,
            "scored_patients": 0,
            "average_score": None,
            "band_counts": {"strong": 0, "steady": 0, "fragile": 0, "at_risk": 0, "unscored": 0},
            "needs_attention": [],
            "unread_alerts": 0,
            "pending_outcomes": 0,
            "checkins_last_7_days": 0,
            "engagement_rate": None,
        }

    band_counts = {"strong": 0, "steady": 0, "fragile": 0, "at_risk": 0, "unscored": 0}
    scores = []
    rows = []

    for patient_oid in assigned:
        patient = await db.users.find_one({"_id": patient_oid, "role": "patient"})
        if not patient:
            continue

        score = await recovery.calculate_recovery_score(patient_oid)
        band = score.get("band") or "unscored"
        band_counts[band] = band_counts.get(band, 0) + 1
        if score.get("score") is not None:
            scores.append(score["score"])

        last_checkin = await db.daily_checkins.find_one(
            {"patient_id": patient_oid}, sort=[("date", -1)]
        )
        unread = await db.alerts.count_documents({
            "target_user_id": to_object_id(doctor_id),
            "patient_id": patient_oid,
            "is_read": False,
        })

        rows.append({
            "patient_id": str(patient_oid),
            "full_name": patient.get("full_name", "Patient"),
            "score": score.get("score"),
            "band": score.get("band"),
            "trend": score.get("trend"),
            "abstinence_days": score.get("abstinence_days"),
            "unread_alerts": unread,
            "last_checkin_date": last_checkin.get("date") if last_checkin else None,
            "weakest_area": (
                min(score["components"], key=lambda c: c["subscore"])["label"]
                if score.get("components") else None
            ),
        })

    # Triage: at-risk, then fragile, then unread alerts; unscored patients last.
    priority = {"at_risk": 0, "fragile": 1, "steady": 2, "strong": 3, None: 4}
    needs_attention = sorted(
        [r for r in rows if r["band"] in ("at_risk", "fragile") or r["unread_alerts"] > 0],
        key=lambda r: (priority.get(r["band"], 4), -r["unread_alerts"], r["score"] or 0),
    )

    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    checkins_7d = await db.daily_checkins.count_documents({
        "patient_id": {"$in": assigned},
        "created_at": {"$gte": seven_days_ago},
    })

    unread_total = await db.alerts.count_documents({
        "target_user_id": to_object_id(doctor_id),
        "is_read": False,
    })
    pending_outcomes = await db.interventions.count_documents({
        "doctor_id": to_object_id(doctor_id),
        "outcome_status": "pending",
    })

    # Expected check-ins over the window is one per patient per day
    expected = len(rows) * 7
    engagement = round(checkins_7d / expected * 100) if expected else None

    return {
        "total_patients": len(rows),
        "scored_patients": len(scores),
        "average_score": round(sum(scores) / len(scores)) if scores else None,
        "band_counts": band_counts,
        "needs_attention": needs_attention[:10],
        "unread_alerts": unread_total,
        "pending_outcomes": pending_outcomes,
        "checkins_last_7_days": checkins_7d,
        "engagement_rate": engagement,
    }


# ── Recovery Score ───────────────────────────────────────────

async def get_patient_recovery_score(
    doctor_id: str, patient_id: str, window_days: int = 30
) -> dict:
    """Recovery score for an assigned patient, through the shared access check."""
    from app.clinical import service as clinical_service
    from app.common import recovery

    patient_oid = await clinical_service.resolve_patient_access(
        {"id": doctor_id, "role": "doctor"}, patient_id
    )
    return await recovery.calculate_recovery_score(patient_oid, window_days)


async def get_patient_digital_twin(
    doctor_id: str, patient_id: str, window_days: int = 30, horizon_days: int = 30
) -> dict:
    """Digital twin for an assigned patient, through the shared access check."""
    from app.clinical import service as clinical_service
    from app.common import recovery

    patient_oid = await clinical_service.resolve_patient_access(
        {"id": doctor_id, "role": "doctor"}, patient_id
    )
    return await recovery.build_digital_twin(patient_oid, window_days, horizon_days)


# ── Check-ins ────────────────────────────────────────────────

async def get_patient_checkins(
    doctor_id: str, patient_id: str, limit: int = 30
) -> list[dict]:
    """Get daily check-ins for a patient."""
    await _verify_assignment(doctor_id, patient_id)
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


# ── Clinical Notes ───────────────────────────────────────────

async def create_clinical_note(
    doctor_id: str, patient_id: str, data: dict
) -> dict:
    """Create a clinical note for a patient."""
    await _verify_assignment(doctor_id, patient_id)
    db = get_db()
    now = datetime.now(timezone.utc)

    doctor = await db.users.find_one({"_id": to_object_id(doctor_id)})

    note_doc = {
        "patient_id": to_object_id(patient_id),
        "doctor_id": to_object_id(doctor_id),
        "doctor_name": doctor["full_name"] if doctor else "Unknown",
        "content": data["content"],
        "note_type": data.get("note_type", "progress"),
        "created_at": now,
    }

    result = await db.clinical_notes.insert_one(note_doc)
    created = await db.clinical_notes.find_one({"_id": result.inserted_id})
    doc = serialize_doc(created)
    doc["patient_id"] = patient_id
    doc["doctor_id"] = doctor_id
    return doc


async def get_clinical_notes(doctor_id: str, patient_id: str) -> list[dict]:
    """Get all clinical notes for a patient."""
    await _verify_assignment(doctor_id, patient_id)
    db = get_db()
    patient_oid = to_object_id(patient_id)

    notes = (
        await db.clinical_notes.find({"patient_id": patient_oid})
        .sort("created_at", -1)
        .to_list(length=200)
    )

    result = []
    for note in notes:
        doc = serialize_doc(note)
        doc["patient_id"] = patient_id
        result.append(doc)

    return result


# ── Recovery Goals ───────────────────────────────────────────

async def create_recovery_goal(
    doctor_id: str, patient_id: str, data: dict
) -> dict:
    """Create a recovery goal for a patient."""
    await _verify_assignment(doctor_id, patient_id)
    db = get_db()
    now = datetime.now(timezone.utc)

    goal_doc = {
        "patient_id": to_object_id(patient_id),
        "doctor_id": to_object_id(doctor_id),
        "title": data["title"],
        "description": data.get("description"),
        "status": "not_started",
        "target_date": data.get("target_date"),
        "notes": None,
        "created_at": now,
        "updated_at": now,
    }

    result = await db.recovery_goals.insert_one(goal_doc)
    created = await db.recovery_goals.find_one({"_id": result.inserted_id})
    doc = serialize_doc(created)
    doc["patient_id"] = patient_id
    return doc


async def get_recovery_goals(doctor_id: str, patient_id: str) -> list[dict]:
    """Get all recovery goals for a patient."""
    await _verify_assignment(doctor_id, patient_id)
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
        result.append(doc)

    return result


async def update_recovery_goal(
    doctor_id: str, patient_id: str, goal_id: str, data: dict
) -> dict:
    """Update a recovery goal's status or notes."""
    await _verify_assignment(doctor_id, patient_id)
    db = get_db()

    goal = await db.recovery_goals.find_one({
        "_id": to_object_id(goal_id),
        "patient_id": to_object_id(patient_id),
    })
    if not goal:
        raise NotFoundError("Recovery Goal")

    update_data = {k: v for k, v in data.items() if v is not None}
    if not update_data:
        raise BadRequestError("No fields to update")

    update_data["updated_at"] = datetime.now(timezone.utc)

    await db.recovery_goals.update_one(
        {"_id": to_object_id(goal_id)},
        {"$set": update_data},
    )

    updated = await db.recovery_goals.find_one({"_id": to_object_id(goal_id)})
    doc = serialize_doc(updated)
    doc["patient_id"] = patient_id
    return doc
