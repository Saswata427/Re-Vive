"""Maps Expo push tokens to users, for every role."""

import re
from datetime import datetime, timezone

from app.database import get_db
from app.common.models import serialize_doc, to_object_id
from app.common.exceptions import BadRequestError, NotFoundError

# The two token shapes Expo issues; anything else is rejected at registration.
_EXPO_TOKEN_RE = re.compile(r"^Expo(nent)?PushToken\[[^\]]+\]$")


async def register_device(user_id: str, data: dict) -> dict:
    """Register a push token, moving it to whoever signed in last on that phone."""
    token = (data.get("token") or "").strip()
    if not _EXPO_TOKEN_RE.match(token):
        raise BadRequestError(
            "Not a valid Expo push token. Expected ExponentPushToken[...]."
        )

    db = get_db()
    now = datetime.now(timezone.utc)

    await db.device_tokens.update_one(
        {"token": token},
        {
            "$set": {
                "user_id": to_object_id(user_id),
                "platform": data.get("platform"),
                "device_label": data.get("device_label"),
                "app_version": data.get("app_version"),
                "last_seen_at": now,
            },
            "$setOnInsert": {"token": token, "created_at": now},
        },
        upsert=True,
    )

    stored = await db.device_tokens.find_one({"token": token})
    return serialize_doc(stored)


async def list_devices(user_id: str) -> list[dict]:
    """List a user's registered devices, most recently seen first."""
    db = get_db()
    raw = (
        await db.device_tokens.find({"user_id": to_object_id(user_id)})
        .sort("last_seen_at", -1)
        .to_list(length=50)
    )
    return [serialize_doc(device) for device in raw]


async def unregister_device(user_id: str, device_id: str) -> None:
    """Remove one of the caller's own devices. Called on sign-out."""
    db = get_db()
    result = await db.device_tokens.delete_one({
        "_id": to_object_id(device_id),
        "user_id": to_object_id(user_id),
    })
    if result.deleted_count == 0:
        raise NotFoundError("Device")
