"""Tests the recovery score engine and digital twin, with the database mocked."""

import asyncio
import sys
import os
from bson import ObjectId
from unittest.mock import AsyncMock, patch, MagicMock

# Ensure backend is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

from app.common import recovery
from app.clinical import schemas as clinical_schemas
from app.main import app


def test_pure_helpers():
    print("[1] Testing pure helpers (_mean, _clamp, _inverse_intensity, _band)...")
    assert recovery._mean([]) == 0.0
    assert recovery._mean([2, 4, 6]) == 4.0

    assert recovery._clamp(-5) == 0.0
    assert recovery._clamp(105) == 100.0
    assert recovery._clamp(50) == 50.0

    # _inverse_intensity: (10 - mean) / 9 * 100
    assert recovery._inverse_intensity([]) == 0.0
    # intensity 1 (lowest/best) -> (10-1)/9 * 100 = 100.0
    assert round(recovery._inverse_intensity([1])) == 100
    # intensity 10 (highest/worst) -> (10-10)/9 * 100 = 0.0
    assert round(recovery._inverse_intensity([10])) == 0
    # intensity 5.5 -> 50.0
    assert round(recovery._inverse_intensity([5.5])) == 50

    # _band
    assert recovery._band(85) == ("strong", "Strong recovery")
    assert recovery._band(80) == ("strong", "Strong recovery")
    assert recovery._band(65) == ("steady", "Steady progress")
    assert recovery._band(45) == ("fragile", "Needs attention")
    assert recovery._band(20) == ("at_risk", "At risk")
    print("  -> Helpers passed.")


def test_component_scorers():
    print("[2] Testing component scorers (_score_sleep, _score_activity, _score_engagement)...")
    # Sleep
    assert recovery._score_sleep([]) == 0.0
    assert recovery._score_sleep([8.0]) == 100.0
    assert recovery._score_sleep([7.0]) == 100.0
    assert recovery._score_sleep([9.0]) == 100.0
    # 3.5h is half of 7.0 -> 50
    assert round(recovery._score_sleep([3.5])) == 50
    # 10h is 1h past 9 -> 100 - 15 = 85
    assert round(recovery._score_sleep([10.0])) == 85

    # Activity
    assert recovery._score_activity([]) == 0.0
    assert recovery._score_activity([30]) == 100.0
    assert recovery._score_activity([15]) == 50.0
    assert recovery._score_activity([60]) == 100.0  # capped

    # Engagement
    assert recovery._score_engagement(set(), 30) == 0.0
    assert recovery._score_engagement({"2026-09-01", "2026-09-02"}, 10) == 20.0
    assert recovery._score_engagement(set(range(30)), 30) == 100.0
    print("  -> Component scorers passed.")


def test_trend_calculation():
    print("[3] Testing trend calculation (_calculate_trend)...")
    # Less than 4 usable checkins -> None
    assert recovery._calculate_trend([]) is None
    assert recovery._calculate_trend([{"craving_level": 3, "stress_level": 3}] * 3) is None

    # Burden falls from 10 (cravings 5 + stress 5) to 4: a change of +6, so improving.
    improving_checkins = [
        {"craving_level": 2, "stress_level": 2},
        {"craving_level": 2, "stress_level": 2},
        {"craving_level": 5, "stress_level": 5},
        {"craving_level": 5, "stress_level": 5},
    ]
    assert recovery._calculate_trend(improving_checkins) == "improving"

    # Declining: recent burden higher than earlier
    declining_checkins = [
        {"craving_level": 7, "stress_level": 7},
        {"craving_level": 7, "stress_level": 7},
        {"craving_level": 2, "stress_level": 2},
        {"craving_level": 2, "stress_level": 2},
    ]
    assert recovery._calculate_trend(declining_checkins) == "declining"

    # Stable: delta between -1.0 and 1.0
    stable_checkins = [
        {"craving_level": 4, "stress_level": 4},
        {"craving_level": 4, "stress_level": 4},
        {"craving_level": 4, "stress_level": 4},
        {"craving_level": 4, "stress_level": 4},
    ]
    assert recovery._calculate_trend(stable_checkins) == "stable"
    print("  -> Trend calculation passed.")


def test_daily_score():
    print("[4] Testing _daily_score...")
    # Perfect day: craving 1, stress 1, sleep 8h, medication taken, activity 30min
    perfect_day = {
        "craving_level": 1,
        "stress_level": 1,
        "sleep_hours": 8.0,
        "medication_taken": True,
        "physical_activity_minutes": 30,
    }
    assert recovery._daily_score(perfect_day) == 100

    # Very bad day: craving 10, stress 10, sleep 2h, no med, activity 0
    bad_day = {
        "craving_level": 10,
        "stress_level": 10,
        "sleep_hours": 2.0,
        "medication_taken": False,
        "physical_activity_minutes": 0,
    }
    score = recovery._daily_score(bad_day)
    assert score < 20
    print("  -> Daily score passed.")


def test_projection_series():
    print("[5] Testing _project_series...")
    pts = recovery._project_series(50, 80, 30)
    assert len(pts) >= 10
    assert pts[0]["day"] == 0
    assert pts[0]["score"] == 50
    assert pts[-1]["day"] == 30
    assert pts[-1]["score"] == 80
    print("  -> Project series passed.")


async def test_recovery_score_cold_start():
    print("[6] Testing calculate_recovery_score cold start (<3 checkins)...")
    patient_oid = ObjectId()
    mock_db = MagicMock()
    # Mock find().sort().to_list() returning 2 checkins
    mock_cursor = MagicMock()
    mock_cursor.sort.return_value = mock_cursor
    mock_cursor.to_list = AsyncMock(return_value=[
        {"date": "2026-09-09", "craving_level": 2},
        {"date": "2026-09-08", "craving_level": 3},
    ])
    mock_db.daily_checkins.find.return_value = mock_cursor

    with patch("app.common.recovery.get_db", return_value=mock_db), \
         patch("app.common.patients.get_profile", AsyncMock(return_value={"abstinence_days": 12})):
        res = await recovery.calculate_recovery_score(patient_oid, window_days=30)
        assert res["score"] is None
        assert res["band"] is None
        assert res["label"] == "Not enough data"
        assert res["checkins_counted"] == 2
        assert "at least 3 check-ins" in res["explanation"]
    print("  -> Cold start passed.")


async def test_recovery_score_populated():
    print("[7] Testing calculate_recovery_score with populated data...")
    patient_oid = ObjectId()
    mock_db = MagicMock()

    checkins = [
        {
            "date": f"2026-09-{i:02d}",
            "craving_level": 2,
            "stress_level": 2,
            "sleep_hours": 8.0,
            "physical_activity_minutes": 30,
            "medication_taken": True,
        }
        for i in range(1, 11)
    ]
    mock_cursor = MagicMock()
    mock_cursor.sort.return_value = mock_cursor
    mock_cursor.to_list = AsyncMock(return_value=checkins)
    mock_db.daily_checkins.find.return_value = mock_cursor
    mock_db.recovery_goals.count_documents = AsyncMock(side_effect=[2, 2]) # total=2, completed=2

    with patch("app.common.recovery.get_db", return_value=mock_db), \
         patch("app.common.patients.get_profile", AsyncMock(return_value={"abstinence_days": 10})):
        res = await recovery.calculate_recovery_score(patient_oid, window_days=30)
        assert res["score"] is not None
        assert 80 <= res["score"] <= 100
        assert res["band"] == "strong"
        assert len(res["components"]) == len(recovery.WEIGHTS)
        assert res["checkins_counted"] == 10
        # Validate Pydantic schema
        valid = clinical_schemas.RecoveryScoreResponse(**res)
        assert valid.score == res["score"]
    print("  -> Populated recovery score passed.")


async def test_digital_twin():
    print("[8] Testing build_digital_twin (cold start and populated)...")
    patient_oid = ObjectId()

    # 1. Cold start
    with patch("app.common.recovery.calculate_recovery_score", AsyncMock(return_value={
        "score": None,
        "band": None,
        "label": "Not enough data",
        "trend": None,
        "checkins_counted": 1,
        "window_days": 30,
        "abstinence_days": 2,
        "components": [],
        "explanation": "Need at least 3 check-ins",
    })):
        twin_cold = await recovery.build_digital_twin(patient_oid)
        assert twin_cold["available"] is False
        assert twin_cold["reason"] == "Need at least 3 check-ins"
        assert twin_cold["scenarios"] == []

    # 2. Populated twin
    baseline_score = {
        "score": 65,
        "band": "steady",
        "label": "Steady progress",
        "trend": "improving",
        "checkins_counted": 14,
        "window_days": 30,
        "abstinence_days": 14,
        "components": [
            {"key": "craving_control", "label": "Craving Control", "subscore": 50, "weight": 25, "contribution": 12.5, "detail": "average craving 5.5/10"},
            {"key": "medication_adherence", "label": "Medication Adherence", "subscore": 70, "weight": 20, "contribution": 14.0, "detail": "7 of 10 taken"},
            {"key": "stress_management", "label": "Stress Management", "subscore": 50, "weight": 15, "contribution": 7.5, "detail": "average stress 5.5/10"},
            {"key": "sleep_quality", "label": "Sleep Quality", "subscore": 60, "weight": 15, "contribution": 9.0, "detail": "averaging 6.0h"},
            {"key": "physical_activity", "label": "Physical Activity", "subscore": 40, "weight": 10, "contribution": 4.0, "detail": "12 min/day"},
            {"key": "engagement", "label": "Check-in Engagement", "subscore": 50, "weight": 10, "contribution": 5.0, "detail": "15 check-ins"},
            {"key": "goal_progress", "label": "Goal Progress", "subscore": 100, "weight": 5, "contribution": 5.0, "detail": "all goals completed"},
        ],
        "explanation": "Scored 65/100 (steady progress)",
    }

    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.sort.return_value = mock_cursor
    checkin_list = [
        {"date": f"2026-09-{i:02d}", "craving_level": 4, "stress_level": 4, "sleep_hours": 7, "medication_taken": True, "physical_activity_minutes": 20}
        for i in range(1, 15)
    ]
    mock_cursor.to_list = AsyncMock(return_value=checkin_list)
    mock_db.daily_checkins.find.return_value = mock_cursor

    with patch("app.common.recovery.calculate_recovery_score", AsyncMock(return_value=baseline_score)), \
         patch("app.common.recovery.get_db", return_value=mock_db):
        twin = await recovery.build_digital_twin(patient_oid, window_days=30, horizon_days=30)
        assert twin["available"] is True
        assert len(twin["scenarios"]) > 0
        assert twin["combined"] is not None
        assert twin["combined"]["projected_score"] > twin["baseline"]["score"]
        assert len(twin["baseline_projection"]) > 0

        # Validate with Pydantic DigitalTwinResponse schema
        twin_model = clinical_schemas.DigitalTwinResponse(**twin)
        assert twin_model.patient_id == str(patient_oid)
        assert twin_model.combined.projected_score == twin["combined"]["projected_score"]
        print(f"  -> Digital twin generated {len(twin_model.scenarios)} scenarios, combined score: {twin_model.combined.projected_score}")
    print("  -> Digital Twin passed.")


def test_fastapi_routes():
    print("[9] Testing FastAPI route registrations...")
    # Read paths from OpenAPI: newer FastAPI nests routers inside app.routes.
    routes = {
        path: {method.upper() for method in ops}
        for path, ops in app.openapi()["paths"].items()
    }

    # Check clinical twin endpoint
    assert "/api/clinical/patients/{patient_id}/digital-twin" in routes
    assert "GET" in routes["/api/clinical/patients/{patient_id}/digital-twin"]

    # Check doctor twin endpoint
    assert "/api/doctor/patients/{patient_id}/digital-twin" in routes
    assert "GET" in routes["/api/doctor/patients/{patient_id}/digital-twin"]

    # Check patient twin endpoint
    assert "/api/patient/digital-twin" in routes
    assert "GET" in routes["/api/patient/digital-twin"]

    # Check timeline endpoint
    assert "/api/clinical/patients/{patient_id}/timeline" in routes
    assert "GET" in routes["/api/clinical/patients/{patient_id}/timeline"]
    print("  -> All twin and recovery routes correctly registered in FastAPI.")


def main():
    print("=== Starting RE:VIVE Recovery & Digital Twin Test Suite ===")
    test_pure_helpers()
    test_component_scorers()
    test_trend_calculation()
    test_daily_score()
    test_projection_series()
    asyncio.run(test_recovery_score_cold_start())
    asyncio.run(test_recovery_score_populated())
    asyncio.run(test_digital_twin())
    test_fastapi_routes()
    print("\n[SUCCESS] ALL 9 TEST SUITES PASSED!")


if __name__ == "__main__":
    main()
