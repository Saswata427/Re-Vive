from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import get_settings, PUBLIC_SECRET_KEYS, DEMO_ADMIN_PASSWORD
from app.database import connect_db, close_db
from app.common.ratelimit import limiter, rate_limit_handler
from app.common.scheduler import start_scheduler, shutdown_scheduler
from app.auth.router import router as auth_router
from app.devices.router import router as devices_router
from app.admin.router import router as admin_router
from app.hospital.router import router as hospital_router
from app.doctor.router import router as doctor_router
from app.patient.router import router as patient_router
from app.guardian.router import router as guardian_router
from app.alerts.router import router as alerts_router
from app.appointments.router import router as appointments_router
from app.clinical.router import router as clinical_router
from app.ai.router import router as ai_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — connect DB on startup, close on shutdown."""
    warn_on_unsafe_defaults()
    await connect_db()
    await seed_admin()
    # Background jobs: the missed check-in sweep
    start_scheduler()
    yield
    shutdown_scheduler()
    await close_db()


def warn_on_unsafe_defaults():
    """Warn when the server runs on the published demo secrets."""
    if settings.SECRET_KEY in PUBLIC_SECRET_KEYS or len(settings.SECRET_KEY) < 32:
        print(
            "[WARN] SECRET_KEY is a published default or too short. Anyone can "
            "forge sign-in tokens. Set a long random SECRET_KEY in backend/.env."
        )
    if settings.ADMIN_PASSWORD == DEMO_ADMIN_PASSWORD:
        print(
            f"[WARN] {settings.ADMIN_EMAIL} is seeded with the demo password. "
            "Set ADMIN_PASSWORD in backend/.env before exposing this server."
        )


async def seed_admin():
    """Create the default admin once, as one upsert so parallel workers don't clash."""
    from pymongo.errors import DuplicateKeyError
    from app.database import get_db
    from app.auth.service import hash_password
    from datetime import datetime, timezone

    db = get_db()
    now = datetime.now(timezone.utc)

    try:
        result = await db.users.update_one(
            {"email": settings.ADMIN_EMAIL},
            {"$setOnInsert": {
                "email": settings.ADMIN_EMAIL,
                "password_hash": hash_password(settings.ADMIN_PASSWORD),
                "role": "admin",
                "full_name": settings.ADMIN_NAME,
                "phone": None,
                "is_active": True,
                "hospital_id": None,
                "assigned_patients": [],
                "linked_patient_id": None,
                "created_at": now,
                "updated_at": now,
            }},
            upsert=True,
        )
    except DuplicateKeyError:
        # Another worker won the race between our upsert's match and its insert
        print(f"[OK] Admin already exists: {settings.ADMIN_EMAIL}")
        return

    if result.upserted_id is not None:
        print(f"[OK] Default admin seeded: {settings.ADMIN_EMAIL}")
    else:
        print(f"[OK] Admin already exists: {settings.ADMIN_EMAIL}")


# ── Create FastAPI App ───────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    description="Healthcare Recovery Management Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── Rate Limiting ────────────────────────────────────────────
# The limiter lives on the app; the limited routes are in auth/router.py.

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
app.add_middleware(SlowAPIMiddleware)

# ── API Routers ──────────────────────────────────────────────

app.include_router(auth_router, prefix="/api")
app.include_router(devices_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(hospital_router, prefix="/api")
app.include_router(doctor_router, prefix="/api")
app.include_router(patient_router, prefix="/api")
app.include_router(guardian_router, prefix="/api")
app.include_router(alerts_router, prefix="/api")
app.include_router(appointments_router, prefix="/api")
app.include_router(clinical_router, prefix="/api")
app.include_router(ai_router, prefix="/api")


# ── Health Check ─────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME}


# ── Serve Frontend Static Files ──────────────────────────────
# Static files at their own paths, index.html for any other page.

frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend")
if os.path.exists(frontend_path):
    css_path = os.path.join(frontend_path, "css")
    js_path = os.path.join(frontend_path, "js")
    assets_path = os.path.join(frontend_path, "assets")

    if os.path.exists(css_path):
        app.mount("/css", StaticFiles(directory=css_path), name="css")
    if os.path.exists(js_path):
        app.mount("/js", StaticFiles(directory=js_path), name="js")
    if os.path.exists(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")

    # SPA fallback middleware: serves index.html for non-API GET requests that 404
    from starlette.middleware.base import BaseHTTPMiddleware
    from fastapi.responses import FileResponse

    class SPAFallbackMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            response = await call_next(request)
            if (
                request.method == "GET"
                and response.status_code == 404
                and not request.url.path.startswith("/api")
                and not request.url.path.startswith("/css")
                and not request.url.path.startswith("/js")
                and not request.url.path.startswith("/assets")
            ):
                index_file = os.path.join(frontend_path, "index.html")
                if os.path.exists(index_file):
                    return FileResponse(index_file)
            return response

    app.add_middleware(SPAFallbackMiddleware)
