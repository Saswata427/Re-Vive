"""One shared rate limiter, in memory; set RATELIMIT_STORAGE_URI to Redis for several workers."""

import os
import warnings

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import get_settings

settings = get_settings()

# Point slowapi at a missing file so it never reads .env itself (it crashed on non-ASCII on Windows).
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", message="Config file .* not found")
    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri=settings.RATELIMIT_STORAGE_URI,
        config_filename=os.path.join(os.path.dirname(__file__), "__no_slowapi_config__"),
    )


def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Return a friendly 429 with a Retry-After header."""
    return JSONResponse(
        status_code=429,
        content={
            "detail": (
                "Too many attempts. Wait a minute before trying again — "
                "if you have forgotten your password, ask your administrator to reset it."
            )
        },
        headers={"Retry-After": "60"},
    )
