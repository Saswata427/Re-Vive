from datetime import datetime, timezone

from app.database import get_db
from app.auth.service import hash_password
from app.common.models import serialize_doc, serialize_docs, to_object_id
from app.common.exceptions import NotFoundError, ConflictError, BadRequestError
from app.common import patients as patient_data


# ── Dashboard Stats ──────────────────────────────────────────

async def get_hospital_dashboard_stats(hospital_id: str) -> dict:
    """Get stats scoped to a specific hospital."""
    db = get_db()
    oid = to_object_id(hospital_id)

    total_doctors = await db.users.count_documents({"hospital_id": oid, "role": "doctor"})
    total_patients = await db.users.count_documents({"hospital_id": oid, "role": "patient"})
    total_guardians = await db.users.count_documents({"hospital_id": oid, "role": "guardian"})
    total_users = total_doctors + total_patients + total_guardians
    active_users = await db.users.count_documents({
        "hospital_id": oid,
        "role": {"$in": ["doctor", "patient", "guardian"]},
        "is_active": True,
    })

    return {
        "total_doctors": total_doctors,
        "total_patients": total_patients,
        "total_guardians": total_guardians,
        "total_users": total_users,
        "active_users": active_users,
    }


# ── User CRUD (hospital-scoped) ─────────────────────────────

async def get_hospital_users(hospital_id: str, role_filter: str = None) -> list[dict]:
    """Get all users belonging to a hospital, optionally filtered by role."""
    db = get_db()
    query = {
        "hospital_id": to_object_id(hospital_id),
        "role": {"$in": ["doctor", "patient", "guardian"]},
    }
    if role_filter and role_filter in ("doctor", "patient", "guardian"):
        query["role"] = role_filter

    users = await db.users.find(query).sort("created_at", -1).to_list(length=1000)
    return serialize_docs(users)


async def create_hospital_user(hospital_id: str, data: dict) -> dict:
    """Create a doctor, patient, or guardian user scoped to a hospital."""
    db = get_db()
    now = datetime.now(timezone.utc)

    allowed_roles = ("doctor", "patient", "guardian")
    if data["role"] not in allowed_roles:
        raise BadRequestError(f"Cannot create user with role '{data['role']}'. Allowed: {', '.join(allowed_roles)}")

    existing = await db.users.find_one({"email": data["email"]})
    if existing:
        raise ConflictError("A user with this email already exists")

    user_doc = {
        "email": data["email"],
        "password_hash": hash_password(data["password"]),
        "role": data["role"],
        "full_name": data["full_name"],
        "phone": data.get("phone"),
        "is_active": True,
        "hospital_id": to_object_id(hospital_id),
        "assigned_patients": [],
        "linked_patient_id": None,
        "created_at": now,
        "updated_at": now,
    }

    result = await db.users.insert_one(user_doc)
    created = await db.users.find_one({"_id": result.inserted_id})
    return serialize_doc(created)


async def update_hospital_user(hospital_id: str, user_id: str, data: dict) -> dict:
    """Update a user belonging to this hospital."""
    db = get_db()

    user = await db.users.find_one({
        "_id": to_object_id(user_id),
        "hospital_id": to_object_id(hospital_id),
        "role": {"$in": ["doctor", "patient", "guardian"]},
    })
    if not user:
        raise NotFoundError("User")

    update_data = {k: v for k, v in data.items() if v is not None}
    if not update_data:
        raise BadRequestError("No fields to update")

    if "email" in update_data:
        existing = await db.users.find_one({
            "email": update_data["email"],
            "_id": {"$ne": to_object_id(user_id)},
        })
        if existing:
            raise ConflictError("A user with this email already exists")

    update_data["updated_at"] = datetime.now(timezone.utc)

    await db.users.update_one(
        {"_id": to_object_id(user_id)},
        {"$set": update_data},
    )

    updated = await db.users.find_one({"_id": to_object_id(user_id)})
    return serialize_doc(updated)


# ── Patient Clinical Profile ─────────────────────────────────

async def _verify_hospital_patient(hospital_id: str, patient_id: str) -> dict:
    """Verify the patient belongs to this hospital. Returns the patient doc."""
    db = get_db()
    patient = await db.users.find_one({
        "_id": to_object_id(patient_id),
        "hospital_id": to_object_id(hospital_id),
        "role": "patient",
    })
    if not patient:
        raise NotFoundError("Patient")
    return patient


async def get_patient_profile(hospital_id: str, patient_id: str) -> dict:
    """Get the clinical profile of a patient in this hospital."""
    await _verify_hospital_patient(hospital_id, patient_id)
    return await patient_data.get_profile(to_object_id(patient_id))


async def update_patient_profile(
    hospital_id: str, patient_id: str, data: dict, updated_by: str
) -> dict:
    """Create or update the clinical profile of a patient in this hospital."""
    await _verify_hospital_patient(hospital_id, patient_id)

    if not any(data.get(field) is not None for field in patient_data.PROFILE_FIELDS):
        raise BadRequestError("No profile fields to update")

    return await patient_data.upsert_profile(
        to_object_id(patient_id), data, updated_by=updated_by
    )


async def update_hospital_user_status(hospital_id: str, user_id: str, is_active: bool) -> dict:
    """Activate or deactivate a user belonging to this hospital."""
    db = get_db()

    user = await db.users.find_one({
        "_id": to_object_id(user_id),
        "hospital_id": to_object_id(hospital_id),
        "role": {"$in": ["doctor", "patient", "guardian"]},
    })
    if not user:
        raise NotFoundError("User")

    now = datetime.now(timezone.utc)
    await db.users.update_one(
        {"_id": to_object_id(user_id)},
        {"$set": {"is_active": is_active, "updated_at": now}},
    )

    updated = await db.users.find_one({"_id": to_object_id(user_id)})
    return serialize_doc(updated)


# ── Doctor-Patient Assignments ───────────────────────────────

async def get_assignments(hospital_id: str) -> list[dict]:
    """Get all doctor-patient assignments for this hospital."""
    db = get_db()
    oid = to_object_id(hospital_id)

    # Find all doctors in this hospital who have assigned patients
    doctors = await db.users.find({
        "hospital_id": oid,
        "role": "doctor",
        "assigned_patients": {"$exists": True, "$ne": []},
    }).to_list(length=500)

    assignments = []
    for doctor in doctors:
        for patient_oid in doctor.get("assigned_patients", []):
            if isinstance(patient_oid, str):
                patient_oid = to_object_id(patient_oid)

            patient = await db.users.find_one({"_id": patient_oid})
            if patient:
                assignments.append({
                    "id": f"{str(doctor['_id'])}_{str(patient_oid)}",
                    "doctor_id": str(doctor["_id"]),
                    "doctor_name": doctor["full_name"],
                    "doctor_email": doctor["email"],
                    "patient_id": str(patient_oid),
                    "patient_name": patient["full_name"],
                    "patient_email": patient["email"],
                    "created_at": str(doctor.get("updated_at", "")),
                })

    return assignments


async def create_assignment(hospital_id: str, doctor_id: str, patient_id: str) -> dict:
    """Assign a doctor to a patient. Both must belong to this hospital."""
    db = get_db()
    oid = to_object_id(hospital_id)

    doctor = await db.users.find_one({
        "_id": to_object_id(doctor_id),
        "hospital_id": oid,
        "role": "doctor",
    })
    if not doctor:
        raise NotFoundError("Doctor")

    patient = await db.users.find_one({
        "_id": to_object_id(patient_id),
        "hospital_id": oid,
        "role": "patient",
    })
    if not patient:
        raise NotFoundError("Patient")

    patient_oid = to_object_id(patient_id)
    if patient_oid in doctor.get("assigned_patients", []):
        raise ConflictError("This patient is already assigned to this doctor")

    now = datetime.now(timezone.utc)
    await db.users.update_one(
        {"_id": to_object_id(doctor_id)},
        {
            "$push": {"assigned_patients": patient_oid},
            "$set": {"updated_at": now},
        },
    )

    return {
        "id": f"{doctor_id}_{patient_id}",
        "doctor_id": doctor_id,
        "doctor_name": doctor["full_name"],
        "doctor_email": doctor["email"],
        "patient_id": patient_id,
        "patient_name": patient["full_name"],
        "patient_email": patient["email"],
        "created_at": str(now),
    }


async def remove_assignment(hospital_id: str, assignment_id: str) -> None:
    """Remove a doctor-patient assignment. assignment_id = 'doctorId_patientId'."""
    db = get_db()
    parts = assignment_id.split("_")
    if len(parts) != 2:
        raise BadRequestError("Invalid assignment ID format")

    doctor_id, patient_id = parts

    doctor = await db.users.find_one({
        "_id": to_object_id(doctor_id),
        "hospital_id": to_object_id(hospital_id),
        "role": "doctor",
    })
    if not doctor:
        raise NotFoundError("Assignment")

    now = datetime.now(timezone.utc)
    await db.users.update_one(
        {"_id": to_object_id(doctor_id)},
        {
            "$pull": {"assigned_patients": to_object_id(patient_id)},
            "$set": {"updated_at": now},
        },
    )


# ── Guardian Linking ─────────────────────────────────────────

async def link_guardian(hospital_id: str, guardian_id: str, patient_id: str) -> dict:
    """Link a guardian to a patient. Both must belong to this hospital."""
    db = get_db()
    oid = to_object_id(hospital_id)

    guardian = await db.users.find_one({
        "_id": to_object_id(guardian_id),
        "hospital_id": oid,
        "role": "guardian",
    })
    if not guardian:
        raise NotFoundError("Guardian")

    patient = await db.users.find_one({
        "_id": to_object_id(patient_id),
        "hospital_id": oid,
        "role": "patient",
    })
    if not patient:
        raise NotFoundError("Patient")

    if guardian.get("linked_patient_id"):
        raise ConflictError("This guardian is already linked to a patient. Unlink first.")

    now = datetime.now(timezone.utc)
    await db.users.update_one(
        {"_id": to_object_id(guardian_id)},
        {"$set": {"linked_patient_id": to_object_id(patient_id), "updated_at": now}},
    )

    return {
        "guardian_id": guardian_id,
        "guardian_name": guardian["full_name"],
        "patient_id": patient_id,
        "patient_name": patient["full_name"],
    }


async def unlink_guardian(hospital_id: str, guardian_id: str) -> None:
    """Remove the guardian-patient link."""
    db = get_db()

    guardian = await db.users.find_one({
        "_id": to_object_id(guardian_id),
        "hospital_id": to_object_id(hospital_id),
        "role": "guardian",
    })
    if not guardian:
        raise NotFoundError("Guardian")

    now = datetime.now(timezone.utc)
    await db.users.update_one(
        {"_id": to_object_id(guardian_id)},
        {"$set": {"linked_patient_id": None, "updated_at": now}},
    )
