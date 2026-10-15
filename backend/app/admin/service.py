from datetime import datetime, timezone
from bson import ObjectId

from app.database import get_db
from app.auth.service import hash_password
from app.common.models import serialize_doc, to_object_id
from app.common.exceptions import NotFoundError, ConflictError, BadRequestError


async def get_platform_stats() -> dict:
    """Get platform-wide statistics for the admin dashboard."""
    db = get_db()

    total_hospitals = await db.hospitals.count_documents({})
    active_hospitals = await db.hospitals.count_documents({"is_active": True})
    total_doctors = await db.users.count_documents({"role": "doctor"})
    total_patients = await db.users.count_documents({"role": "patient"})
    total_guardians = await db.users.count_documents({"role": "guardian"})
    total_users = await db.users.count_documents({})

    return {
        "total_hospitals": total_hospitals,
        "active_hospitals": active_hospitals,
        "total_doctors": total_doctors,
        "total_patients": total_patients,
        "total_guardians": total_guardians,
        "total_users": total_users,
    }


async def create_hospital(data: dict) -> dict:
    """Create a hospital and its admin account."""
    db = get_db()
    now = datetime.now(timezone.utc)

    existing_hospital = await db.hospitals.find_one({"email": data["email"]})
    if existing_hospital:
        raise ConflictError("A hospital with this email already exists")

    existing_user = await db.users.find_one({"email": data["admin_email"]})
    if existing_user:
        raise ConflictError("A user with this admin email already exists")

    admin_user = await db.users.insert_one({
        "email": data["admin_email"],
        "password_hash": hash_password(data["admin_password"]),
        "role": "hospital",
        "full_name": data["admin_name"],
        "phone": None,
        "is_active": True,
        "hospital_id": None,  # Will update after hospital creation
        "assigned_patients": [],
        "linked_patient_id": None,
        "created_at": now,
        "updated_at": now,
    })

    admin_user_id = admin_user.inserted_id

    hospital = await db.hospitals.insert_one({
        "name": data["name"],
        "address": data["address"],
        "phone": data["phone"],
        "email": data["email"],
        "is_active": True,
        "admin_user_id": admin_user_id,
        "created_at": now,
        "updated_at": now,
    })

    hospital_id = hospital.inserted_id

    await db.users.update_one(
        {"_id": admin_user_id},
        {"$set": {"hospital_id": hospital_id}}
    )

    created = await db.hospitals.find_one({"_id": hospital_id})
    result = serialize_doc(created)

    result["admin_name"] = data["admin_name"]
    result["admin_email"] = data["admin_email"]

    return result


# ── Hospital Admin Management ────────────────────────────────

async def _hospital_or_404(hospital_id: str) -> dict:
    """Fetch a hospital or raise 404."""
    db = get_db()
    hospital = await db.hospitals.find_one({"_id": to_object_id(hospital_id)})
    if not hospital:
        raise NotFoundError("Hospital")
    return hospital


def _admin_summary(user: dict, hospital: dict) -> dict:
    """Shape a hospital admin user for the admin API."""
    doc = serialize_doc(dict(user))
    doc.pop("password_hash", None)
    doc["hospital_id"] = str(hospital["_id"])
    doc["hospital_name"] = hospital.get("name")
    return doc


async def get_hospital_admins() -> list[dict]:
    """List every hospital admin account across the platform."""
    db = get_db()

    admins = await db.users.find({"role": "hospital"}).sort("created_at", -1).to_list(length=500)

    hospital_oids = [
        u["hospital_id"] for u in admins if isinstance(u.get("hospital_id"), ObjectId)
    ]
    hospitals: dict[ObjectId, dict] = {}
    if hospital_oids:
        async for h in db.hospitals.find({"_id": {"$in": hospital_oids}}):
            hospitals[h["_id"]] = h

    result = []
    for user in admins:
        hospital = hospitals.get(user.get("hospital_id")) or {"_id": user.get("hospital_id") or ""}
        result.append(_admin_summary(user, hospital))
    return result


async def get_hospital_admin(hospital_id: str) -> dict:
    """Get the admin account for one hospital."""
    db = get_db()
    hospital = await _hospital_or_404(hospital_id)

    admin = await db.users.find_one({
        "_id": hospital.get("admin_user_id"),
        "role": "hospital",
    }) if hospital.get("admin_user_id") else None

    if not admin:
        raise NotFoundError("Hospital admin")

    return _admin_summary(admin, hospital)


async def update_hospital_admin(hospital_id: str, data: dict) -> dict:
    """Update the hospital admin's name, email, or phone."""
    db = get_db()
    hospital = await _hospital_or_404(hospital_id)
    admin_uid = hospital.get("admin_user_id")
    if not admin_uid:
        raise NotFoundError("Hospital admin")

    updates = {k: v for k, v in data.items() if v is not None}
    if not updates:
        raise BadRequestError("No fields to update")

    if "email" in updates:
        clash = await db.users.find_one({
            "email": updates["email"],
            "_id": {"$ne": admin_uid},
        })
        if clash:
            raise ConflictError("A user with this email already exists")

    updates["updated_at"] = datetime.now(timezone.utc)
    await db.users.update_one({"_id": admin_uid}, {"$set": updates})

    updated = await db.users.find_one({"_id": admin_uid})
    return _admin_summary(updated, hospital)


async def reset_hospital_admin_password(hospital_id: str, new_password: str) -> dict:
    """Set a new password for the hospital admin."""
    db = get_db()
    hospital = await _hospital_or_404(hospital_id)
    admin_uid = hospital.get("admin_user_id")
    if not admin_uid:
        raise NotFoundError("Hospital admin")

    await db.users.update_one(
        {"_id": admin_uid},
        {"$set": {
            "password_hash": hash_password(new_password),
            "updated_at": datetime.now(timezone.utc),
        }},
    )

    updated = await db.users.find_one({"_id": admin_uid})
    return _admin_summary(updated, hospital)


async def replace_hospital_admin(hospital_id: str, data: dict) -> dict:
    """Hand a hospital to a new admin; the old one is deactivated, not deleted."""
    db = get_db()
    hospital = await _hospital_or_404(hospital_id)
    now = datetime.now(timezone.utc)

    existing = await db.users.find_one({"email": data["admin_email"]})
    if existing:
        raise ConflictError("A user with this email already exists")

    previous_uid = hospital.get("admin_user_id")

    new_admin = await db.users.insert_one({
        "email": data["admin_email"],
        "password_hash": hash_password(data["admin_password"]),
        "role": "hospital",
        "full_name": data["admin_name"],
        "phone": data.get("admin_phone"),
        "is_active": hospital.get("is_active", True),
        "hospital_id": hospital["_id"],
        "assigned_patients": [],
        "linked_patient_id": None,
        "created_at": now,
        "updated_at": now,
    })

    await db.hospitals.update_one(
        {"_id": hospital["_id"]},
        {"$set": {"admin_user_id": new_admin.inserted_id, "updated_at": now}},
    )

    # Retire the outgoing admin — deactivated, never deleted
    if previous_uid:
        await db.users.update_one(
            {"_id": previous_uid},
            {"$set": {"is_active": False, "updated_at": now}},
        )

    hospital = await db.hospitals.find_one({"_id": hospital["_id"]})
    created = await db.users.find_one({"_id": new_admin.inserted_id})
    return _admin_summary(created, hospital)


async def get_all_hospitals() -> list[dict]:
    """Get all hospitals with their admin user info."""
    db = get_db()

    hospitals = await db.hospitals.find().sort("created_at", -1).to_list(length=500)
    result = []

    for hospital in hospitals:
        # Save ObjectId ref before serialization converts it to string
        admin_uid = hospital.get("admin_user_id")
        doc = serialize_doc(hospital)

        if admin_uid:
            admin_user = await db.users.find_one({"_id": admin_uid})
            if admin_user:
                doc["admin_name"] = admin_user["full_name"]
                doc["admin_email"] = admin_user["email"]

        result.append(doc)

    return result


async def get_hospital_by_id(hospital_id: str) -> dict:
    """Get a single hospital by ID."""
    db = get_db()
    hospital = await db.hospitals.find_one({"_id": to_object_id(hospital_id)})
    if not hospital:
        raise NotFoundError("Hospital")

    doc = serialize_doc(hospital)

    if hospital.get("admin_user_id"):
        admin_user = await db.users.find_one({"_id": hospital["admin_user_id"]})
        if admin_user:
            doc["admin_name"] = admin_user["full_name"]
            doc["admin_email"] = admin_user["email"]

    return doc


async def update_hospital(hospital_id: str, data: dict) -> dict:
    """Update hospital details."""
    db = get_db()

    update_data = {k: v for k, v in data.items() if v is not None}
    if not update_data:
        raise BadRequestError("No fields to update")

    update_data["updated_at"] = datetime.now(timezone.utc)

    if "email" in update_data:
        existing = await db.hospitals.find_one({
            "email": update_data["email"],
            "_id": {"$ne": to_object_id(hospital_id)}
        })
        if existing:
            raise ConflictError("A hospital with this email already exists")

    result = await db.hospitals.update_one(
        {"_id": to_object_id(hospital_id)},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise NotFoundError("Hospital")

    return await get_hospital_by_id(hospital_id)


async def update_hospital_status(hospital_id: str, is_active: bool) -> dict:
    """Activate or deactivate a hospital and its admin user."""
    db = get_db()
    now = datetime.now(timezone.utc)

    hospital = await db.hospitals.find_one({"_id": to_object_id(hospital_id)})
    if not hospital:
        raise NotFoundError("Hospital")

    await db.hospitals.update_one(
        {"_id": to_object_id(hospital_id)},
        {"$set": {"is_active": is_active, "updated_at": now}}
    )

    # Also activate/deactivate the hospital admin user
    if hospital.get("admin_user_id"):
        await db.users.update_one(
            {"_id": hospital["admin_user_id"]},
            {"$set": {"is_active": is_active, "updated_at": now}}
        )

    # If deactivating, also deactivate all users belonging to this hospital
    if not is_active:
        await db.users.update_many(
            {"hospital_id": to_object_id(hospital_id)},
            {"$set": {"is_active": False, "updated_at": now}}
        )

    return await get_hospital_by_id(hospital_id)
