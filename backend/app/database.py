from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import get_settings

settings = get_settings()

client: AsyncIOMotorClient = None
db: AsyncIOMotorDatabase = None


async def connect_db():
    """Initialize the Motor client and database connection."""
    global client, db
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.DATABASE_NAME]

    await db.users.create_index("email", unique=True)
    await db.hospitals.create_index("email", unique=True)
    await db.patient_profiles.create_index("user_id", unique=True)
    await db.daily_checkins.create_index([("patient_id", 1), ("date", -1)])
    await db.clinical_notes.create_index([("patient_id", 1), ("created_at", -1)])
    await db.recovery_goals.create_index("patient_id")
    await db.medications.create_index([("patient_id", 1), ("is_active", -1)])
    await db.vitals.create_index([("patient_id", 1), ("recorded_at", -1)])
    await db.interventions.create_index([("patient_id", 1), ("created_at", -1)])
    await db.treatment_plans.create_index([("patient_id", 1), ("is_current", -1)])
    await db.appointments.create_index([("patient_id", 1), ("date_time", 1)])
    await db.appointments.create_index([("doctor_id", 1), ("date_time", 1)])
    await db.alerts.create_index([("target_user_id", 1), ("is_read", 1)])
    await db.alerts.create_index([("target_user_id", 1), ("created_at", -1)])
    await db.alerts.create_index([("patient_id", 1), ("alert_type", 1), ("created_at", -1)])
    await db.audit_logs.create_index([("user_id", 1), ("created_at", -1)])

    # Refresh tokens: found by hash, listed per user, removed by TTL once expired.
    await db.refresh_tokens.create_index("token_hash", unique=True)
    await db.refresh_tokens.create_index([("user_id", 1), ("issued_at", -1)])
    await db.refresh_tokens.create_index("expires_at", expireAfterSeconds=0)

    # One push token per install, so a shared phone only alerts its current user.
    await db.device_tokens.create_index("token", unique=True)
    await db.device_tokens.create_index([("user_id", 1), ("last_seen_at", -1)])

    print(f"[OK] Connected to MongoDB: {settings.DATABASE_NAME}")


async def close_db():
    """Close the Motor client connection."""
    if client:
        client.close()
        print("[OK] MongoDB connection closed")


def get_db() -> AsyncIOMotorDatabase:
    """Get the database instance."""
    return db
