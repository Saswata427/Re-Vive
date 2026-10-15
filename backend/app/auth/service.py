import hashlib
import secrets
from datetime import datetime, timedelta, timezone
import bcrypt
from bson import ObjectId
from jose import JWTError, jwt
from app.config import get_settings

settings = get_settings()


# ── Passwords ────────────────────────────────────────────────
# Plain bcrypt (passlib breaks on bcrypt 4.1+); old passlib hashes still verify.

# bcrypt only reads 72 bytes, so cut there ourselves and behave the same on every version.
_BCRYPT_MAX_BYTES = 72


def _password_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt()).decode("ascii")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a password against its hash; a broken hash just fails the sign-in."""
    try:
        return bcrypt.checkpw(
            _password_bytes(plain_password), hashed_password.encode("utf-8")
        )
    except (ValueError, TypeError):
        return False


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Create a signed access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict | None:
    """Decode a token, or return None if it's invalid."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


# ── Refresh Tokens ───────────────────────────────────────────
# Short-lived JWTs plus revocable refresh tokens, stored only as SHA-256 hashes.


def _hash_refresh_token(token: str) -> str:
    """Hash a refresh token for storage. See the note above on why SHA-256."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def issue_refresh_token(
    user_id: str,
    device_label: str = None,
    user_agent: str = None,
    replaces: ObjectId = None,
) -> tuple[str, datetime]:
    """Create a refresh token, store its hash and return the plain token this once."""
    from app.database import get_db

    db = get_db()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    token = secrets.token_urlsafe(48)

    await db.refresh_tokens.insert_one({
        "user_id": ObjectId(user_id),
        "token_hash": _hash_refresh_token(token),
        "device_label": device_label,
        "user_agent": user_agent,
        "issued_at": now,
        "expires_at": expires_at,
        "revoked_at": None,
        "replaced_by": None,
        "replaces": replaces,
    })

    return token, expires_at


async def rotate_refresh_token(
    token: str, user_agent: str = None
) -> tuple[dict, str, datetime] | None:
    """Rotate a refresh token; reusing an old one signs the user out everywhere."""
    from app.database import get_db

    db = get_db()
    now = datetime.now(timezone.utc)
    token_hash = _hash_refresh_token(token)

    stored = await db.refresh_tokens.find_one({"token_hash": token_hash})
    if not stored:
        return None

    if stored.get("revoked_at") is not None:
        # A rotated token used again means theft, so end every session; a signed-out one is just refused.
        if stored.get("replaced_by") is not None:
            await revoke_all_for_user(str(stored["user_id"]))
        return None

    expires_at = stored.get("expires_at")
    if isinstance(expires_at, datetime):
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= now:
            return None

    user = await db.users.find_one({"_id": stored["user_id"]})
    if not user or not user.get("is_active", False):
        return None

    new_token, new_expires = await issue_refresh_token(
        user_id=str(user["_id"]),
        device_label=stored.get("device_label"),
        user_agent=user_agent or stored.get("user_agent"),
        replaces=stored["_id"],
    )

    await db.refresh_tokens.update_one(
        {"_id": stored["_id"]},
        {"$set": {
            "revoked_at": now,
            "replaced_by": _hash_refresh_token(new_token),
        }},
    )

    return user, new_token, new_expires


async def revoke_refresh_token(token: str) -> bool:
    """Revoke a single refresh token. Returns whether one was actually revoked."""
    from app.database import get_db

    db = get_db()
    result = await db.refresh_tokens.update_one(
        {"token_hash": _hash_refresh_token(token), "revoked_at": None},
        {"$set": {"revoked_at": datetime.now(timezone.utc)}},
    )
    return result.modified_count > 0


async def revoke_all_for_user(user_id: str) -> int:
    """Revoke every live refresh token for a user. Returns how many were revoked."""
    from app.database import get_db

    db = get_db()
    result = await db.refresh_tokens.update_many(
        {"user_id": ObjectId(user_id), "revoked_at": None},
        {"$set": {"revoked_at": datetime.now(timezone.utc)}},
    )
    return result.modified_count
