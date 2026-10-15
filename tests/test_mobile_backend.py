"""Tests refresh tokens, devices, push and the scheduler on a throwaway database."""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from bson import ObjectId

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

TEST_DB = "revive_mobile_test_db"
os.environ["DATABASE_NAME"] = TEST_DB
# The scheduler test needs it on, whatever backend/.env says.
os.environ["SCHEDULER_ENABLED"] = "true"

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app import database  # noqa: E402
from app.auth import service as auth_service  # noqa: E402
from app.common import alerts as alert_engine  # noqa: E402
from app.common import push, scheduler  # noqa: E402
from app.devices import service as device_service  # noqa: E402
from app.common.exceptions import BadRequestError, NotFoundError  # noqa: E402

passed = 0


def check(label: str, condition: bool) -> None:
    global passed
    if not condition:
        raise AssertionError(f"FAILED: {label}")
    passed += 1
    print(f"    ok  {label}")


async def make_user(email: str, role: str = "patient", active: bool = True) -> str:
    db = database.get_db()
    result = await db.users.insert_one({
        "email": email,
        "password_hash": "x",
        "role": role,
        "full_name": "Test User",
        "is_active": active,
        "assigned_patients": [],
        "linked_patient_id": None,
        "created_at": datetime.now(timezone.utc),
    })
    return str(result.inserted_id)


# ── Refresh tokens ───────────────────────────────────────────

async def test_issue_and_rotate():
    print("\n[1] Issuing and rotating refresh tokens")
    db = database.get_db()
    user_id = await make_user("rotate@test.com")

    token, expires = await auth_service.issue_refresh_token(user_id, device_label="Pixel 8")
    check("issue returns a plaintext token", isinstance(token, str) and len(token) > 40)
    check("expiry is in the future", expires > datetime.now(timezone.utc))

    stored = await db.refresh_tokens.find_one({"user_id": ObjectId(user_id)})
    check("plaintext token is NOT stored", stored["token_hash"] != token)
    check("stored hash matches", stored["token_hash"] == auth_service._hash_refresh_token(token))
    check("device label persisted", stored["device_label"] == "Pixel 8")

    rotated = await auth_service.rotate_refresh_token(token)
    check("rotation succeeds", rotated is not None)

    user, new_token, _ = rotated
    check("rotation returns the right user", str(user["_id"]) == user_id)
    check("a different token is issued", new_token != token)
    check("device label carries across rotation",
          (await db.refresh_tokens.find_one({
              "token_hash": auth_service._hash_refresh_token(new_token)
          }))["device_label"] == "Pixel 8")

    old = await db.refresh_tokens.find_one({"token_hash": auth_service._hash_refresh_token(token)})
    check("the presented token is revoked", old["revoked_at"] is not None)
    check("revoked token records its successor", old["replaced_by"] is not None)

    again = await auth_service.rotate_refresh_token(new_token)
    check("the new token itself rotates", again is not None)


async def test_reuse_detection():
    print("\n[2] Reuse of a rotated token burns the whole family")
    db = database.get_db()
    user_id = await make_user("reuse@test.com")

    token, _ = await auth_service.issue_refresh_token(user_id)
    _, second, _ = await auth_service.rotate_refresh_token(token)
    _, third, _ = await auth_service.rotate_refresh_token(second)

    live = await db.refresh_tokens.count_documents(
        {"user_id": ObjectId(user_id), "revoked_at": None}
    )
    check("exactly one live token after two rotations", live == 1)

    # An attacker replays the token they stole two rotations ago.
    replay = await auth_service.rotate_refresh_token(token)
    check("replaying a revoked token is refused", replay is None)

    live_after = await db.refresh_tokens.count_documents(
        {"user_id": ObjectId(user_id), "revoked_at": None}
    )
    check("every live session was revoked by the reuse check", live_after == 0)

    stranded = await auth_service.rotate_refresh_token(third)
    check("the legitimate holder is signed out too", stranded is None)


async def test_expiry_and_inactive():
    print("\n[3] Expired tokens and deactivated accounts")
    db = database.get_db()

    user_id = await make_user("expired@test.com")
    token, _ = await auth_service.issue_refresh_token(user_id)
    await db.refresh_tokens.update_one(
        {"token_hash": auth_service._hash_refresh_token(token)},
        {"$set": {"expires_at": datetime.now(timezone.utc) - timedelta(days=1)}},
    )
    check("an expired token is refused", await auth_service.rotate_refresh_token(token) is None)

    inactive_id = await make_user("inactive@test.com", active=False)
    inactive_token, _ = await auth_service.issue_refresh_token(inactive_id)
    check("a deactivated account cannot refresh",
          await auth_service.rotate_refresh_token(inactive_token) is None)

    check("an unknown token is refused",
          await auth_service.rotate_refresh_token("not-a-real-token") is None)


async def test_revocation():
    print("\n[4] Revocation")
    db = database.get_db()
    user_id = await make_user("revoke@test.com")

    a, _ = await auth_service.issue_refresh_token(user_id, device_label="phone")
    b, _ = await auth_service.issue_refresh_token(user_id, device_label="tablet")

    check("revoking one token reports success", await auth_service.revoke_refresh_token(a) is True)
    check("revoking it again reports nothing to do",
          await auth_service.revoke_refresh_token(a) is False)
    check("the revoked session cannot refresh", await auth_service.rotate_refresh_token(a) is None)

    still_live = await auth_service.rotate_refresh_token(b)
    check("the other device is unaffected", still_live is not None)

    _, b2, _ = still_live
    await auth_service.issue_refresh_token(user_id, device_label="laptop")
    count = await auth_service.revoke_all_for_user(user_id)
    check("sign-out-everywhere revokes every live session", count == 2)
    check("nothing live remains",
          await db.refresh_tokens.count_documents(
              {"user_id": ObjectId(user_id), "revoked_at": None}) == 0)


# ── Device registration ──────────────────────────────────────

async def test_device_registration():
    print("\n[5] Device registration")
    db = database.get_db()
    user_id = await make_user("device@test.com")
    token = "ExponentPushToken[aaaaaaaaaaaaaaaaaaaaaa]"

    device = await device_service.register_device(user_id, {
        "token": token, "platform": "android", "device_label": "Pixel 8",
    })
    check("registration returns the device", device["token"] == token)
    check("owner recorded", device["user_id"] == user_id)

    await device_service.register_device(user_id, {
        "token": token, "platform": "android", "device_label": "Pixel 8 Pro",
    })
    check("re-registering does not duplicate",
          await db.device_tokens.count_documents({"token": token}) == 1)
    check("re-registering refreshes metadata",
          (await db.device_tokens.find_one({"token": token}))["device_label"] == "Pixel 8 Pro")

    # The privacy case: a second account signs in on the same physical phone.
    other_id = await make_user("shared@test.com", role="doctor")
    await device_service.register_device(other_id, {"token": token, "platform": "android"})
    moved = await db.device_tokens.find_one({"token": token})
    check("the token moves to the new account", str(moved["user_id"]) == other_id)
    check("the previous owner no longer receives its pushes",
          await db.device_tokens.count_documents({"user_id": ObjectId(user_id)}) == 0)

    for bad in ("plain-string", "ExponentPushToken", "", "fcm:abc123"):
        try:
            await device_service.register_device(user_id, {"token": bad})
            raise AssertionError(f"expected rejection for {bad!r}")
        except BadRequestError:
            pass
    check("malformed push tokens are rejected", True)

    check("ExpoPushToken[...] is also accepted",
          (await device_service.register_device(
              user_id, {"token": "ExpoPushToken[bbbbbbbbbbbb]"}))["token"].startswith("ExpoPushToken"))

    listed = await device_service.list_devices(user_id)
    check("listing returns only the caller's devices", len(listed) == 1)

    try:
        await device_service.unregister_device(other_id, listed[0]["id"])
        raise AssertionError("expected a 404 unregistering another user's device")
    except NotFoundError:
        pass
    check("one user cannot unregister another's device", True)

    await device_service.unregister_device(user_id, listed[0]["id"])
    check("unregistering removes it", await device_service.list_devices(user_id) == [])


# ── Push dispatch ────────────────────────────────────────────

async def test_push_dispatch():
    print("\n[6] Push dispatch")
    db = database.get_db()
    doctor_id = await make_user("pushdoc@test.com", role="doctor")
    patient_id = await make_user("pushpat@test.com", role="patient")

    await db.users.update_one(
        {"_id": ObjectId(doctor_id)},
        {"$set": {"assigned_patients": [ObjectId(patient_id)]}},
    )
    await device_service.register_device(doctor_id, {
        "token": "ExponentPushToken[dddddddddddddddddddddd]", "platform": "ios",
    })

    tokens = await push.get_device_tokens([ObjectId(doctor_id)])
    check("tokens resolve for a user", len(tokens) == 1)
    check("no tokens for a user with no devices",
          await push.get_device_tokens([ObjectId(patient_id)]) == [])

    check("titles map from alert type",
          push.alert_title("craving_spike", "high") == "Craving spike")
    check("critical severity is marked urgent",
          push.alert_title("craving_spike", "critical").startswith("Urgent"))
    check("unknown alert types still get a title",
          push.alert_title("some_future_ai_flag", "low") == "Clinical alert")

    # An alert must reach the care team even when Expo is unreachable.
    with patch("app.common.push.notify_users",
               AsyncMock(side_effect=RuntimeError("expo is down"))):
        try:
            await alert_engine.broadcast_alert(
                ObjectId(patient_id), "craving_spike", "high", "Craving 9/10",
            )
            raised = False
        except RuntimeError:
            raised = True
    check("a push failure propagates only if unguarded (sanity)", raised is True)

    # The real guard: send_to_tokens swallows transport failures.
    with patch("httpx.AsyncClient.post", AsyncMock(side_effect=RuntimeError("network down"))):
        sent = await push.send_to_tokens(["ExponentPushToken[x]"], "t", "b")
    check("transport failure returns 0 rather than raising", sent == 0)

    before = await db.alerts.count_documents({"patient_id": ObjectId(patient_id)})
    with patch("httpx.AsyncClient.post", AsyncMock(side_effect=RuntimeError("network down"))):
        recipients = await alert_engine.broadcast_alert(
            ObjectId(patient_id), "craving_spike", "high", "Craving 9/10",
        )
    after = await db.alerts.count_documents({"patient_id": ObjectId(patient_id)})
    check("alerts are still written when push fails", after == before + recipients)
    check("the doctor was a recipient", recipients >= 1)

    with patch.object(push.settings, "PUSH_ENABLED", False):
        check("disabling push short-circuits",
              await push.notify_users([ObjectId(doctor_id)], "t", "b") == 0)


async def test_dead_token_pruning():
    print("\n[7] Dead token pruning")
    db = database.get_db()
    user_id = await make_user("dead@test.com")
    dead = "ExponentPushToken[deaddeaddeaddeaddead]"
    live = "ExponentPushToken[livelivelivelivelive]"
    await device_service.register_device(user_id, {"token": dead})
    await device_service.register_device(user_id, {"token": live})

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"data": [
                {"status": "error", "message": "not registered",
                 "details": {"error": "DeviceNotRegistered"}},
                {"status": "ok", "id": "receipt-1"},
            ]}

    with patch("httpx.AsyncClient.post", AsyncMock(return_value=FakeResponse())):
        accepted = await push.send_to_tokens([dead, live], "title", "body")

    check("only the good token counts as accepted", accepted == 1)
    check("the dead token was pruned",
          await db.device_tokens.count_documents({"token": dead}) == 0)
    check("the live token survived",
          await db.device_tokens.count_documents({"token": live}) == 1)


# ── Scheduler ────────────────────────────────────────────────

async def test_scheduler():
    print("\n[8] Scheduler")
    check("not running before start", scheduler.is_running() is False)

    fallback = await alert_engine.maybe_scan_missed_checkins()
    check("traffic-driven fallback works when no scheduler runs", isinstance(fallback, int))

    scheduler.start_scheduler()
    check("scheduler starts", scheduler.is_running() is True)
    check("traffic-driven sweep stands down while the scheduler runs",
          await alert_engine.maybe_scan_missed_checkins() == 0)

    scheduler.shutdown_scheduler()
    check("scheduler stops", scheduler.is_running() is False)


# ── Runner ───────────────────────────────────────────────────

async def main():
    settings = get_settings()
    if settings.DATABASE_NAME != TEST_DB:
        raise SystemExit(
            f"Refusing to run: settings point at {settings.DATABASE_NAME!r}, not the "
            f"throwaway {TEST_DB!r}. Is DATABASE_NAME pinned in backend/.env?"
        )

    print(f"=== RE:VIVE mobile backend suite (db: {TEST_DB}) ===")
    await database.connect_db()
    await database.get_db().client.drop_database(TEST_DB)
    await database.connect_db()

    try:
        await test_issue_and_rotate()
        await test_reuse_detection()
        await test_expiry_and_inactive()
        await test_revocation()
        await test_device_registration()
        await test_push_dispatch()
        await test_dead_token_pruning()
        await test_scheduler()
    finally:
        await database.get_db().client.drop_database(TEST_DB)
        await database.close_db()
        print(f"\n[cleanup] dropped {TEST_DB}")

    print(f"\n[SUCCESS] {passed} assertions passed.")


if __name__ == "__main__":
    asyncio.run(main())
