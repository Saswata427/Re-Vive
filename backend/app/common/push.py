"""Expo push delivery, best effort: the alert is already saved, so a failed push never fails the request."""

import logging
from bson import ObjectId

from app.config import get_settings
from app.database import get_db

logger = logging.getLogger(__name__)
settings = get_settings()

# Expo accepts at most 100 messages per request.
_CHUNK_SIZE = 100

# Expo's reply for an uninstalled app; those tokens get deleted.
_DEAD_TOKEN_ERRORS = {"DeviceNotRegistered", "InvalidCredentials"}

# Severities that should break through a quiet phone.
_HIGH_PRIORITY = {"high", "critical"}


async def get_device_tokens(user_oids: list[ObjectId]) -> list[str]:
    """Collect every registered Expo push token for the given users."""
    if not user_oids:
        return []

    db = get_db()
    tokens = []
    async for device in db.device_tokens.find(
        {"user_id": {"$in": user_oids}}, {"token": 1}
    ):
        token = device.get("token")
        if token:
            tokens.append(token)
    return tokens


async def _prune_tokens(tokens: list[str]) -> None:
    """Delete tokens Expo has told us are dead."""
    if not tokens:
        return
    db = get_db()
    await db.device_tokens.delete_many({"token": {"$in": tokens}})
    logger.info("Pruned %d dead push token(s)", len(tokens))


def _chunk(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i:i + size]


async def send_to_tokens(
    tokens: list[str],
    title: str,
    body: str,
    data: dict = None,
    severity: str = None,
) -> int:
    """Send one notification to many tokens and never raise. Returns how many were accepted."""
    if not settings.PUSH_ENABLED or not tokens:
        return 0

    try:
        import httpx
    except ImportError:
        logger.warning("httpx is not installed; push notifications are disabled")
        return 0

    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if settings.EXPO_ACCESS_TOKEN:
        headers["Authorization"] = f"Bearer {settings.EXPO_ACCESS_TOKEN}"

    priority = "high" if severity in _HIGH_PRIORITY else "default"
    accepted = 0
    dead: list[str] = []

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            for batch in _chunk(tokens, _CHUNK_SIZE):
                messages = [
                    {
                        "to": token,
                        "title": title,
                        "body": body,
                        "data": data or {},
                        "sound": "default",
                        "priority": priority,
                        "channelId": "clinical-alerts",
                    }
                    for token in batch
                ]

                response = await client.post(
                    settings.EXPO_PUSH_URL, json=messages, headers=headers
                )
                response.raise_for_status()

                # Receipts come back in the order we sent, so the index finds the token.
                receipts = response.json().get("data", [])
                for index, receipt in enumerate(receipts):
                    if receipt.get("status") == "ok":
                        accepted += 1
                        continue
                    error = (receipt.get("details") or {}).get("error")
                    if error in _DEAD_TOKEN_ERRORS and index < len(batch):
                        dead.append(batch[index])
                    else:
                        logger.warning(
                            "Expo rejected a push: %s", receipt.get("message")
                        )
    except Exception as exc:
        logger.warning("Push dispatch failed: %s", exc)

    if dead:
        try:
            await _prune_tokens(dead)
        except Exception as exc:
            logger.warning("Could not prune dead push tokens: %s", exc)

    return accepted


async def notify_users(
    user_oids: list[ObjectId],
    title: str,
    body: str,
    data: dict = None,
    severity: str = None,
) -> int:
    """Push a notification to every device belonging to the given users."""
    if not settings.PUSH_ENABLED or not user_oids:
        return 0

    try:
        tokens = await get_device_tokens(user_oids)
    except Exception as exc:
        logger.warning("Could not resolve push tokens: %s", exc)
        return 0

    return await send_to_tokens(tokens, title, body, data, severity)


# ── Presentation ─────────────────────────────────────────────

_ALERT_TITLES = {
    "craving_spike": "Craving spike",
    "stress_spike": "Raised stress",
    "adherence_drop": "Medication missed",
    "missed_checkin": "No check-in",
    "appointment": "Appointment update",
}


def alert_title(alert_type: str, severity: str) -> str:
    """A short notification title for an alert type."""
    title = _ALERT_TITLES.get(alert_type, "Clinical alert")
    if severity == "critical":
        return f"Urgent — {title.lower()}"
    return title
