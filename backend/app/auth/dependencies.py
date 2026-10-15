from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Annotated
from bson import ObjectId

from app.database import get_db
from app.auth.service import decode_token
from app.auth.schemas import UserRole
from app.common.exceptions import UnauthorizedError, ForbiddenError
from app.common.models import serialize_doc

security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> dict:
    """Return the signed-in user from the bearer token."""
    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        raise UnauthorizedError("Invalid or expired token")

    user_id = payload.get("sub")
    if user_id is None:
        raise UnauthorizedError("Invalid token payload")

    db = get_db()
    user = await db.users.find_one({"_id": ObjectId(user_id)})

    if user is None:
        raise UnauthorizedError("User not found")

    if not user.get("is_active", False):
        raise ForbiddenError("Account is deactivated")

    return serialize_doc(user)


def role_required(*roles: UserRole):
    """Dependency that only lets the given roles through."""
    async def _role_checker(
        current_user: Annotated[dict, Depends(get_current_user)],
    ) -> dict:
        user_role = current_user.get("role")
        allowed = [r.value if isinstance(r, UserRole) else r for r in roles]
        if user_role not in allowed:
            raise ForbiddenError(
                f"Role '{user_role}' is not authorized. Required: {', '.join(allowed)}"
            )
        return current_user

    return _role_checker
