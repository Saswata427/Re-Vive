from pydantic import Field
from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path
from typing import Optional

BACKEND_DIR = Path(__file__).resolve().parent.parent

# Published demo defaults: fine locally, never in production (main.py warns).
PUBLIC_SECRET_KEYS = {
    "revive-super-secret-key-change-in-production-2024",
    "CHANGE_ME_IN_PRODUCTION",
}
DEMO_ADMIN_PASSWORD = "admin123"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # MongoDB
    MONGODB_URI: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "revive_db"

    # JWT
    SECRET_KEY: str = "revive-super-secret-key-change-in-production-2024"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        15,
        description=(
            "Access token lifetime. Short by design: a JWT cannot be revoked before "
            "it expires, so the window in which a stolen one is useful is exactly "
            "this value. Long sessions come from the refresh token instead. A client "
            "with no refresh flow will be signed out this often — raise it only for "
            "such a client, and understand that is the trade."
        ),
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        30,
        description="How long a session survives without re-entering a password.",
    )

    # App
    APP_NAME: str = "RE:VIVE"
    DEBUG: bool = True

    # Recovery Risk AI microservice
    AI_SERVICE_URL: str = "http://127.0.0.1:8010"
    AI_SERVICE_TIMEOUT_SECONDS: float = 15.0

    # Security
    CORS_ORIGINS: str = Field(
        "http://localhost:8000,http://127.0.0.1:8000",
        description="Comma-separated list of allowed origins. Never use '*' in production.",
    )
    LOGIN_RATE_LIMIT: str = Field(
        "5/minute",
        description="Rate limit applied per IP to POST /api/auth/login",
    )
    RATELIMIT_STORAGE_URI: Optional[str] = Field(
        None,
        description=(
            "Shared rate-limit store (e.g. redis://localhost:6379) for multi-worker "
            "deployments. Unset means slowapi's in-memory store, which is per process."
        ),
    )

    # Push notifications (Expo)
    PUSH_ENABLED: bool = True
    EXPO_PUSH_URL: str = "https://exp.host/--/api/v2/push/send"
    EXPO_ACCESS_TOKEN: Optional[str] = Field(
        None,
        description=(
            "Only needed once push security is enabled on the Expo project. "
            "Unset works for development and Expo Go."
        ),
    )

    # Background scheduler
    SCHEDULER_ENABLED: bool = True
    MISSED_CHECKIN_SCAN_MINUTES: int = Field(
        15,
        description=(
            "Interval for the missed check-in sweep. Replaces the traffic-driven "
            "throttle, which raised alerts late on a quiet system."
        ),
    )

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse CORS_ORIGINS into a list, dropping blanks."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # Default Admin
    ADMIN_EMAIL: str = "admin@revive.com"
    ADMIN_PASSWORD: str = DEMO_ADMIN_PASSWORD
    ADMIN_NAME: str = "System Admin"

    # Always read backend/.env as UTF-8, wherever the server is started from.
    model_config = {
        "env_file": BACKEND_DIR / ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
