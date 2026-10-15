"""Clinical alerts: every rule and recipient lives here."""

from datetime import datetime, timezone, timedelta
from bson import ObjectId

from app.database import get_db
from app.common import push


# ── Alert Types ──────────────────────────────────────────────

ALERT_CRAVING_SPIKE = "craving_spike"
ALERT_STRESS_SPIKE = "stress_spike"
ALERT_ADHERENCE_DROP = "adherence_drop"
ALERT_MISSED_CHECKIN = "missed_checkin"
ALERT_APPOINTMENT = "appointment"

# ── Severities ───────────────────────────────────────────────

SEVERITY_LOW = "low"
SEVERITY_MEDIUM = "medium"
SEVERITY_HIGH = "high"
SEVERITY_CRITICAL = "critical"

# ── Trigger Thresholds ───────────────────────────────────────

CRAVING_THRESHOLD = 8          # craving_level at or above this raises an alert
CRITICAL_CRAVING_THRESHOLD = 10
STRESS_THRESHOLD = 8           # stress_level at or above this raises an alert
MISSED_CHECKIN_HOURS = 48

# Medication adherence: this many misses within the trailing window raises a flag
ADHERENCE_WINDOW = 3
ADHERENCE_MISS_THRESHOLD = 2


# ── Recipient Resolution ─────────────────────────────────────

async def get_alert_recipients(patient_oid: ObjectId) -> list[ObjectId]:
    """Resolve who should be notified about a patient: assigned doctors + guardian."""
    db = get_db()
    recipients: list[ObjectId] = []

    doctor_cursor = db.users.find(
        {"role": "doctor", "assigned_patients": patient_oid, "is_active": True},
        {"_id": 1},
    )
    async for doctor in doctor_cursor:
        recipients.append(doctor["_id"])

    guardian = await db.users.find_one(
        {"role": "guardian", "linked_patient_id": patient_oid, "is_active": True},
        {"_id": 1},
    )
    if guardian:
        recipients.append(guardian["_id"])

    return recipients


async def _patient_name(patient_oid: ObjectId) -> str:
    """Look up a patient's display name, falling back to a generic label."""
    db = get_db()
    patient = await db.users.find_one({"_id": patient_oid}, {"full_name": 1})
    return patient.get("full_name", "Patient") if patient else "Patient"


# ── Alert Creation ───────────────────────────────────────────

async def create_alert(
    target_user_id: ObjectId,
    patient_id: ObjectId,
    alert_type: str,
    severity: str,
    message: str,
) -> ObjectId:
    """Insert a single alert document and return its ID."""
    db = get_db()
    result = await db.alerts.insert_one({
        "target_user_id": target_user_id,
        "patient_id": patient_id,
        "alert_type": alert_type,
        "severity": severity,
        "message": message,
        "is_read": False,
        "created_at": datetime.now(timezone.utc),
    })
    return result.inserted_id


async def broadcast_alert(
    patient_oid: ObjectId,
    alert_type: str,
    severity: str,
    message: str,
    extra_recipients: list[ObjectId] = None,
) -> int:
    """Send one alert to the whole care team, then push it. Returns how many were created."""
    recipients = await get_alert_recipients(patient_oid)
    for extra in (extra_recipients or []):
        if extra not in recipients:
            recipients.append(extra)

    for target in recipients:
        await create_alert(target, patient_oid, alert_type, severity, message)

    await push.notify_users(
        recipients,
        title=push.alert_title(alert_type, severity),
        body=message,
        data={
            "alert_type": alert_type,
            "severity": severity,
            "patient_id": str(patient_oid),
        },
        severity=severity,
    )

    return len(recipients)


# ── Check-in Evaluation ──────────────────────────────────────

async def evaluate_checkin(patient_oid: ObjectId, checkin: dict) -> int:
    """Raise alerts for high cravings, high stress or missed medication in a check-in."""
    created = 0
    name = await _patient_name(patient_oid)

    craving = checkin.get("craving_level")
    if craving is not None and craving >= CRAVING_THRESHOLD:
        severity = (
            SEVERITY_CRITICAL
            if craving >= CRITICAL_CRAVING_THRESHOLD
            else SEVERITY_HIGH
        )
        created += await broadcast_alert(
            patient_oid,
            ALERT_CRAVING_SPIKE,
            severity,
            f"{name} reported a craving level of {craving}/10",
        )

    stress = checkin.get("stress_level")
    if stress is not None and stress >= STRESS_THRESHOLD:
        created += await broadcast_alert(
            patient_oid,
            ALERT_STRESS_SPIKE,
            SEVERITY_MEDIUM,
            f"{name} reported a stress level of {stress}/10",
        )

    if checkin.get("medication_taken") is False:
        created += await _evaluate_adherence(patient_oid, name)

    return created


async def _evaluate_adherence(patient_oid: ObjectId, name: str) -> int:
    """Alert on repeated missed medication, at most once a day per patient."""
    db = get_db()

    recent = (
        await db.daily_checkins.find(
            {"patient_id": patient_oid},
            {"medication_taken": 1},
        ).sort("date", -1).to_list(length=ADHERENCE_WINDOW)
    )

    missed = sum(1 for ci in recent if ci.get("medication_taken") is False)
    if missed < ADHERENCE_MISS_THRESHOLD:
        return 0

    if await _already_alerted_recently(patient_oid, ALERT_ADHERENCE_DROP):
        return 0

    return await broadcast_alert(
        patient_oid,
        ALERT_ADHERENCE_DROP,
        SEVERITY_HIGH,
        f"{name} has missed medication {missed} of the last {len(recent)} check-ins",
    )


# ── Missed Check-in Sweep ────────────────────────────────────

async def _already_alerted_recently(
    patient_oid: ObjectId, alert_type: str, hours: int = 24
) -> bool:
    """Guard against duplicate alerts for the same patient within a window."""
    db = get_db()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    existing = await db.alerts.find_one({
        "patient_id": patient_oid,
        "alert_type": alert_type,
        "created_at": {"$gte": cutoff},
    })
    return existing is not None


async def scan_missed_checkins() -> int:
    """Alert for patients silent over 48 hours, at most once a day each."""
    db = get_db()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=MISSED_CHECKIN_HOURS)
    created = 0

    patient_cursor = db.users.find(
        {"role": "patient", "is_active": True},
        {"_id": 1, "full_name": 1, "created_at": 1},
    )

    async for patient in patient_cursor:
        patient_oid = patient["_id"]

        latest = await db.daily_checkins.find_one(
            {"patient_id": patient_oid},
            sort=[("created_at", -1)],
        )

        if latest:
            last_seen = latest.get("created_at")
        else:
            # Never checked in — measure silence from account creation
            last_seen = patient.get("created_at")

        if not isinstance(last_seen, datetime):
            continue

        # Mongo returns naive UTC datetimes; normalize before comparing
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)

        if last_seen > cutoff:
            continue

        if await _already_alerted_recently(patient_oid, ALERT_MISSED_CHECKIN):
            continue

        hours_silent = int(
            (datetime.now(timezone.utc) - last_seen).total_seconds() // 3600
        )
        name = patient.get("full_name", "Patient")
        created += await broadcast_alert(
            patient_oid,
            ALERT_MISSED_CHECKIN,
            SEVERITY_MEDIUM,
            f"{name} has not checked in for {hours_silent} hours",
        )

    return created


# The sweep scans every patient, so run it at most once per interval.
SCAN_INTERVAL_MINUTES = 15
_last_scan_at: datetime = None


async def maybe_scan_missed_checkins() -> int:
    """Fallback sweep for when the scheduler is off; does nothing while it runs."""
    from app.common import scheduler

    if scheduler.is_running():
        return 0

    global _last_scan_at
    now = datetime.now(timezone.utc)

    if _last_scan_at is not None:
        if now - _last_scan_at < timedelta(minutes=SCAN_INTERVAL_MINUTES):
            return 0

    _last_scan_at = now
    return await scan_missed_checkins()
