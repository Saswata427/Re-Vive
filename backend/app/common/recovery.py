"""Recovery score engine: a 0-100 score with its breakdown, worked out on request and never stored."""

from datetime import datetime, timezone, timedelta, date
from bson import ObjectId

from app.database import get_db
from app.common import patients as patient_data


# ── Tuning ───────────────────────────────────────────────────

SCORE_WINDOW_DAYS = 30          # trailing window the score reads
MIN_CHECKINS_FOR_SCORE = 3      # below this the score is null, not zero
ACTIVITY_TARGET_MINUTES = 30    # daily activity that earns full marks
SLEEP_IDEAL_LOW = 7.0
SLEEP_IDEAL_HIGH = 9.0

# Component weights, summing to 100
WEIGHTS = {
    "craving_control": 25,
    "medication_adherence": 20,
    "stress_management": 15,
    "sleep_quality": 15,
    "physical_activity": 10,
    "engagement": 10,
    "goal_progress": 5,
}

COMPONENT_LABELS = {
    "craving_control": "Craving Control",
    "medication_adherence": "Medication Adherence",
    "stress_management": "Stress Management",
    "sleep_quality": "Sleep Quality",
    "physical_activity": "Physical Activity",
    "engagement": "Check-in Engagement",
    "goal_progress": "Goal Progress",
}

# Score bands used for the headline label
BANDS = (
    (80, "strong", "Strong recovery"),
    (60, "steady", "Steady progress"),
    (40, "fragile", "Needs attention"),
    (0, "at_risk", "At risk"),
)


# ── Helpers ──────────────────────────────────────────────────

def _mean(values: list) -> float:
    return sum(values) / len(values) if values else 0.0


def _clamp(value: float) -> float:
    """Keep a subscore inside 0-100."""
    return max(0.0, min(100.0, value))


def _inverse_intensity(values: list) -> float:
    """Map a 1-10 intensity (where lower is better) onto a 0-100 subscore."""
    if not values:
        return 0.0
    return _clamp((10 - _mean(values)) / 9 * 100)


def _band(score: float) -> tuple:
    for threshold, key, label in BANDS:
        if score >= threshold:
            return key, label
    return BANDS[-1][1], BANDS[-1][2]


# ── Component Scoring ────────────────────────────────────────

def _score_sleep(hours: list) -> float:
    """Full marks inside the 7-9h band, tapering by distance outside it."""
    if not hours:
        return 0.0

    nightly = []
    for h in hours:
        if SLEEP_IDEAL_LOW <= h <= SLEEP_IDEAL_HIGH:
            nightly.append(100.0)
        elif h < SLEEP_IDEAL_LOW:
            # 0h scores 0, 7h scores 100
            nightly.append(_clamp(h / SLEEP_IDEAL_LOW * 100))
        else:
            # Each hour past 9 costs 15 points
            nightly.append(_clamp(100 - (h - SLEEP_IDEAL_HIGH) * 15))

    return _clamp(_mean(nightly))


def _score_activity(minutes: list) -> float:
    """Daily minutes against the target, capped so extra effort cannot inflate."""
    if not minutes:
        return 0.0
    daily = [_clamp(m / ACTIVITY_TARGET_MINUTES * 100) for m in minutes]
    return _clamp(_mean(daily))


def _score_engagement(checkin_dates: set, window_days: int) -> float:
    """Share of the window's days that carry a check-in."""
    if window_days <= 0:
        return 0.0
    return _clamp(len(checkin_dates) / window_days * 100)


def _describe(key: str, subscore: float, detail: str) -> str:
    """One plain-language sentence explaining a component's subscore."""
    if subscore >= 80:
        quality = "strong"
    elif subscore >= 60:
        quality = "steady"
    elif subscore >= 40:
        quality = "mixed"
    else:
        quality = "weak"
    return f"{COMPONENT_LABELS[key]} is {quality} — {detail}."


# ── Public API ───────────────────────────────────────────────

async def calculate_recovery_score(
    patient_oid: ObjectId, window_days: int = SCORE_WINDOW_DAYS
) -> dict:
    """A patient's recovery score and breakdown; the score is None with too little data."""
    db = get_db()
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    cutoff_str = cutoff.strftime("%Y-%m-%d")

    checkins = (
        await db.daily_checkins.find({
            "patient_id": patient_oid,
            "date": {"$gte": cutoff_str},
        }).sort("date", -1).to_list(length=window_days + 10)
    )

    profile = await patient_data.get_profile(patient_oid)

    # Cold start — say so rather than reporting a misleading zero
    if len(checkins) < MIN_CHECKINS_FOR_SCORE:
        return {
            "score": None,
            "band": None,
            "label": "Not enough data",
            "trend": None,
            "checkins_counted": len(checkins),
            "window_days": window_days,
            "abstinence_days": profile.get("abstinence_days"),
            "components": [],
            "explanation": (
                f"A recovery score needs at least {MIN_CHECKINS_FOR_SCORE} check-ins "
                f"in the last {window_days} days. This patient has "
                f"{len(checkins)}."
            ),
        }

    cravings = [c["craving_level"] for c in checkins if c.get("craving_level") is not None]
    stresses = [c["stress_level"] for c in checkins if c.get("stress_level") is not None]
    sleeps = [c["sleep_hours"] for c in checkins if c.get("sleep_hours") is not None]
    activity = [
        c.get("physical_activity_minutes") or 0
        for c in checkins
        if c.get("physical_activity_minutes") is not None
    ]
    meds = [c["medication_taken"] for c in checkins if c.get("medication_taken") is not None]
    checkin_dates = {c["date"] for c in checkins if c.get("date")}

    # Goals contribute completion rate
    total_goals = await db.recovery_goals.count_documents({"patient_id": patient_oid})
    completed_goals = await db.recovery_goals.count_documents({
        "patient_id": patient_oid, "status": "completed",
    })

    subscores = {
        "craving_control": _inverse_intensity(cravings),
        "stress_management": _inverse_intensity(stresses),
        "sleep_quality": _score_sleep(sleeps),
        "medication_adherence": (
            _clamp(sum(1 for m in meds if m) / len(meds) * 100) if meds else 0.0
        ),
        "physical_activity": _score_activity(activity),
        "engagement": _score_engagement(checkin_dates, window_days),
        "goal_progress": (
            _clamp(completed_goals / total_goals * 100) if total_goals else 100.0
        ),
    }

    details = {
        "craving_control": (
            f"average craving {_mean(cravings):.1f}/10" if cravings else "no craving data"
        ),
        "stress_management": (
            f"average stress {_mean(stresses):.1f}/10" if stresses else "no stress data"
        ),
        "sleep_quality": (
            f"averaging {_mean(sleeps):.1f}h a night" if sleeps else "no sleep data"
        ),
        "medication_adherence": (
            f"{sum(1 for m in meds if m)} of {len(meds)} doses taken"
            if meds else "no medication data"
        ),
        "physical_activity": (
            f"averaging {_mean(activity):.0f} min a day against a "
            f"{ACTIVITY_TARGET_MINUTES} min target"
            if activity else "no activity data"
        ),
        "engagement": (
            f"{len(checkin_dates)} check-ins in {window_days} days"
        ),
        "goal_progress": (
            f"{completed_goals} of {total_goals} goals completed"
            if total_goals else "no goals set yet"
        ),
    }

    score = sum(subscores[k] * WEIGHTS[k] / 100 for k in WEIGHTS)
    score = round(_clamp(score))
    band, label = _band(score)

    components = [
        {
            "key": key,
            "label": COMPONENT_LABELS[key],
            "subscore": round(subscores[key]),
            "weight": WEIGHTS[key],
            "contribution": round(subscores[key] * WEIGHTS[key] / 100, 1),
            "detail": _describe(key, subscores[key], details[key]),
        }
        for key in sorted(WEIGHTS, key=lambda k: -WEIGHTS[k])
    ]

    trend = _calculate_trend(checkins)

    weakest = min(components, key=lambda c: c["subscore"])
    strongest = max(components, key=lambda c: c["subscore"])
    explanation = (
        f"Scored {score}/100 ({label.lower()}) from {len(checkins)} check-ins over "
        f"{window_days} days. Strongest area: {strongest['label'].lower()} "
        f"({strongest['subscore']}/100). Needs most attention: "
        f"{weakest['label'].lower()} ({weakest['subscore']}/100)."
    )

    return {
        "score": score,
        "band": band,
        "label": label,
        "trend": trend,
        "checkins_counted": len(checkins),
        "window_days": window_days,
        "abstinence_days": profile.get("abstinence_days"),
        "components": components,
        "explanation": explanation,
    }


def _calculate_trend(checkins: list) -> str:
    """Compare cravings and stress in the recent half against the earlier half."""
    usable = [
        c for c in checkins
        if c.get("craving_level") is not None and c.get("stress_level") is not None
    ]
    if len(usable) < 4:
        return None

    # checkins arrive newest-first
    midpoint = len(usable) // 2
    recent = usable[:midpoint]
    earlier = usable[midpoint:]

    def burden(group):
        return _mean([c["craving_level"] + c["stress_level"] for c in group])

    delta = burden(earlier) - burden(recent)

    if delta >= 1.0:
        return "improving"
    if delta <= -1.0:
        return "declining"
    return "stable"


# ── Timeline ─────────────────────────────────────────────────

async def get_recovery_timeline(patient_oid: ObjectId, days: int = 30) -> dict:
    """Group the patient's history by day, with a daily score on check-in days."""
    from app.clinical import service as clinical_service

    db = get_db()
    history = await clinical_service.get_medical_history(patient_oid, limit=300)

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    # Daily point-in-time scores from the check-ins themselves
    checkins = (
        await db.daily_checkins.find({
            "patient_id": patient_oid,
            "date": {"$gte": cutoff},
        }).sort("date", -1).to_list(length=days + 10)
    )
    daily_scores = {c["date"]: _daily_score(c) for c in checkins if c.get("date")}

    buckets: dict[str, list] = {}
    for event in history["events"]:
        occurred = (event.get("occurred_at") or "")[:10]
        if not occurred or occurred < cutoff:
            continue
        buckets.setdefault(occurred, []).append(event)

    entries = [
        {
            "date": day,
            "daily_score": daily_scores.get(day),
            "events": sorted(
                buckets[day], key=lambda e: e.get("occurred_at", ""), reverse=True
            ),
            "event_count": len(buckets[day]),
        }
        for day in sorted(buckets, reverse=True)
    ]

    return {
        "patient_id": str(patient_oid),
        "patient_name": history["patient_name"],
        "days": days,
        "entries": entries,
        "total_events": sum(e["event_count"] for e in entries),
    }


def _daily_score(checkin: dict) -> int:
    """One day's score from that day's values alone."""
    parts = {
        "craving_control": _inverse_intensity(
            [checkin["craving_level"]] if checkin.get("craving_level") is not None else []
        ),
        "stress_management": _inverse_intensity(
            [checkin["stress_level"]] if checkin.get("stress_level") is not None else []
        ),
        "sleep_quality": _score_sleep(
            [checkin["sleep_hours"]] if checkin.get("sleep_hours") is not None else []
        ),
        "medication_adherence": 100.0 if checkin.get("medication_taken") else 0.0,
        "physical_activity": _score_activity(
            [checkin.get("physical_activity_minutes") or 0]
        ),
    }

    total_weight = sum(WEIGHTS[k] for k in parts)
    score = sum(parts[k] * WEIGHTS[k] for k in parts) / total_weight
    return round(_clamp(score))


# ── Digital Twin ─────────────────────────────────────────────
# Move one component toward a healthy target and rerun the same weighted score.

TWIN_HORIZON_DAYS = 30

TWIN_DISCLAIMER = (
    "This is a simplified prototype, not a clinically validated simulator. Each "
    "projection re-runs the recovery-score formula with a single input changed "
    "and assumes the change is adopted steadily over the horizon. Real recovery "
    "is not linear and depends on factors the score does not capture."
)

# "target" sets a subscore outright; "delta" adds to where the patient is now.
TWIN_SCENARIOS = [
    {
        "key": "improve_sleep",
        "component": "sleep_quality",
        "mode": "target",
        "value": 90.0,
        "label": "Sleep settles into the 7–9 hour band",
        "rationale": "Most nights fall inside the healthy range.",
    },
    {
        "key": "improve_adherence",
        "component": "medication_adherence",
        "mode": "target",
        "value": 100.0,
        "label": "Every dose taken",
        "rationale": "No missed medication across the window.",
    },
    {
        "key": "reduce_cravings",
        "component": "craving_control",
        "mode": "delta",
        "value": 200.0 / 9,  # ~2 points on the 1–10 craving scale
        "label": "Cravings ease by about two points",
        "rationale": "Average craving intensity drops roughly two points on the 1–10 scale.",
    },
    {
        "key": "reduce_stress",
        "component": "stress_management",
        "mode": "delta",
        "value": 200.0 / 9,
        "label": "Stress eases by about two points",
        "rationale": "Average stress intensity drops roughly two points on the 1–10 scale.",
    },
    {
        "key": "increase_activity",
        "component": "physical_activity",
        "mode": "target",
        "value": 100.0,
        "label": "Activity reaches the 30-minute daily target",
        "rationale": "At least half an hour of activity on most days.",
    },
    {
        "key": "daily_checkins",
        "component": "engagement",
        "mode": "target",
        "value": 100.0,
        "label": "A check-in every day",
        "rationale": "The whole window is logged.",
    },
]


def _project_series(start_score: float, end_score: float, horizon_days: int) -> list:
    """A straight-line ramp from start to end, sampled about a dozen times."""
    step = max(1, horizon_days // 12)
    days = list(range(0, horizon_days + 1, step))
    if days[-1] != horizon_days:
        days.append(horizon_days)
    out = []
    for d in days:
        frac = d / horizon_days if horizon_days else 1.0
        out.append({
            "day": d,
            "score": round(_clamp(start_score + (end_score - start_score) * frac)),
        })
    return out


def _baseline_trajectory(checkins: list, current_score: float, horizon_days: int) -> dict:
    """Project the score from the last two weeks' trend; flat when there are too few days."""
    pts = []
    for c in checkins:
        raw = (c.get("date") or "")[:10]
        try:
            day = date.fromisoformat(raw)
        except ValueError:
            continue
        pts.append((day, float(_daily_score(c))))

    pts.sort(key=lambda p: p[0])
    pts = pts[-14:]

    if len(pts) < 4:
        return {
            "slope_per_week": 0.0,
            "modelled": False,
            "points": _project_series(current_score, current_score, horizon_days),
        }

    base_day = pts[0][0]
    xs = [(day - base_day).days for day, _ in pts]
    ys = [s for _, s in pts]
    n = len(pts)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    denom = sum((x - mean_x) ** 2 for x in xs) or 1.0
    slope = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n)) / denom
    end = _clamp(current_score + slope * horizon_days)

    return {
        "slope_per_week": round(slope * 7, 1),
        "modelled": True,
        "points": _project_series(current_score, end, horizon_days),
    }


async def build_digital_twin(
    patient_oid: ObjectId,
    window_days: int = SCORE_WINDOW_DAYS,
    horizon_days: int = TWIN_HORIZON_DAYS,
) -> dict:
    """Digital twin: the current breakdown, a no-change path and one projection per scenario."""
    baseline = await calculate_recovery_score(patient_oid, window_days)

    result = {
        "patient_id": str(patient_oid),
        "window_days": window_days,
        "horizon_days": horizon_days,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": TWIN_DISCLAIMER,
        "available": baseline["score"] is not None,
        "reason": None if baseline["score"] is not None else baseline["explanation"],
        "baseline": baseline,
        "baseline_projection": [],
        "baseline_slope_per_week": 0.0,
        "scenarios": [],
        "combined": None,
    }

    if baseline["score"] is None:
        return result

    db = get_db()
    cutoff_str = (
        datetime.now(timezone.utc) - timedelta(days=window_days)
    ).strftime("%Y-%m-%d")
    checkins = (
        await db.daily_checkins.find({
            "patient_id": patient_oid,
            "date": {"$gte": cutoff_str},
        }).sort("date", -1).to_list(length=window_days + 10)
    )

    traj = _baseline_trajectory(checkins, baseline["score"], horizon_days)
    result["baseline_projection"] = traj["points"]
    result["baseline_slope_per_week"] = traj["slope_per_week"]

    subs = {c["key"]: float(c["subscore"]) for c in baseline["components"]}

    scenarios = []
    total_delta = 0.0
    for cfg in TWIN_SCENARIOS:
        comp = cfg["component"]
        s0 = subs.get(comp, 0.0)
        s1 = cfg["value"] if cfg["mode"] == "target" else s0 + cfg["value"]
        s1 = _clamp(min(100.0, s1))
        gain = s1 - s0
        if gain <= 0.5:
            # already at or above where this scenario would take them
            continue

        weight = WEIGHTS[comp]
        delta_points = round(gain * weight / 100, 1)
        projected = round(_clamp(baseline["score"] + delta_points))
        p_band, p_label = _band(projected)
        total_delta += gain * weight / 100

        scenarios.append({
            "key": cfg["key"],
            "label": cfg["label"],
            "rationale": cfg["rationale"],
            "component": comp,
            "component_label": COMPONENT_LABELS[comp],
            "baseline_subscore": round(s0),
            "projected_subscore": round(s1),
            "score_delta": delta_points,
            "projected_score": projected,
            "projected_band": p_band,
            "projected_label": p_label,
            "projection": _project_series(baseline["score"], projected, horizon_days),
        })

    scenarios.sort(key=lambda s: -s["score_delta"])
    result["scenarios"] = scenarios

    if scenarios:
        combined_score = round(_clamp(baseline["score"] + total_delta))
        c_band, c_label = _band(combined_score)
        result["combined"] = {
            "label": "Every change above, together",
            "projected_score": combined_score,
            "score_delta": round(total_delta, 1),
            "projected_band": c_band,
            "projected_label": c_label,
            "projection": _project_series(
                baseline["score"], combined_score, horizon_days
            ),
        }

    return result
