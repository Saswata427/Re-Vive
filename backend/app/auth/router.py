from fastapi import APIRouter, Depends, Request
from typing import Annotated

from app.database import get_db
from app.auth.schemas import (
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    TokenResponse,
    UserResponse,
)
from app.auth.service import (
    create_access_token,
    issue_refresh_token,
    revoke_all_for_user,
    revoke_refresh_token,
    rotate_refresh_token,
    verify_password,
)
from app.auth.dependencies import get_current_user
from app.common.exceptions import UnauthorizedError
from app.common.audit import log_action
from app.common.ratelimit import limiter
from app.config import get_settings

settings = get_settings()

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.LOGIN_RATE_LIMIT)
async def login(request: Request, body: LoginRequest):
    """Sign in with email and password. Rate limited, so `request` must stay in the signature."""
    db = get_db()
    user = await db.users.find_one({"email": body.email})

    if not user:
        raise UnauthorizedError("Invalid email or password")

    if not verify_password(body.password, user["password_hash"]):
        raise UnauthorizedError("Invalid email or password")

    if not user.get("is_active", False):
        raise UnauthorizedError("Account is deactivated. Contact your administrator.")

    token = create_access_token(
        data={
            "sub": str(user["_id"]),
            "role": user["role"],
            "email": user["email"],
        }
    )

    refresh_token, _ = await issue_refresh_token(
        user_id=str(user["_id"]),
        device_label=body.device_label,
        user_agent=request.headers.get("user-agent"),
    )

    await log_action(
        user_id=str(user["_id"]),
        action="login",
        resource_type="auth",
        details={"device_label": body.device_label} if body.device_label else None,
        ip_address=request.client.host if request.client else None,
    )

    return TokenResponse(
        access_token=token,
        role=user["role"],
        user_id=str(user["_id"]),
        full_name=user["full_name"],
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit(settings.LOGIN_RATE_LIMIT)
async def refresh(request: Request, body: RefreshRequest):
    """Swap a refresh token for a new pair. Rate limited like sign-in."""
    rotated = await rotate_refresh_token(
        body.refresh_token,
        user_agent=request.headers.get("user-agent"),
    )

    if rotated is None:
        # One message for every bad token, so an attacker can't tell which case they hit.
        raise UnauthorizedError("Session expired. Please sign in again.")

    user, new_refresh_token, _ = rotated

    token = create_access_token(
        data={
            "sub": str(user["_id"]),
            "role": user["role"],
            "email": user["email"],
        }
    )

    return TokenResponse(
        access_token=token,
        role=user["role"],
        user_id=str(user["_id"]),
        full_name=user["full_name"],
        refresh_token=new_refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    body: LogoutRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Sign out. Revokes one session, or all of them when no token is given."""
    if body.refresh_token:
        await revoke_refresh_token(body.refresh_token)
        message = "Signed out on this device."
    else:
        count = await revoke_all_for_user(current_user["id"])
        message = f"Signed out of {count} session{'' if count == 1 else 's'}."

    await log_action(
        user_id=current_user["id"],
        action="logout",
        resource_type="auth",
        details={"scope": "single" if body.refresh_token else "all"},
        ip_address=request.client.host if request.client else None,
    )

    return MessageResponse(message=message)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: Annotated[dict, Depends(get_current_user)]):
    """Get the current authenticated user's profile."""
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        full_name=current_user["full_name"],
        phone=current_user.get("phone"),
        role=current_user["role"],
        is_active=current_user["is_active"],
        hospital_id=current_user.get("hospital_id"),
        created_at=str(current_user.get("created_at", "")),
    )
