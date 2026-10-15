"""Recovery Risk AI: an XGBoost risk estimate with SHAP reasons. No auth, so bind it to 127.0.0.1."""

import os
from pathlib import Path
from typing import Any, Optional

import joblib
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from pymongo import MongoClient
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier


# ── Configuration ────────────────────────────────────────────
# Read this folder's .env as UTF-8.

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", encoding="utf-8")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
MONGO_DB = os.getenv("MONGO_DB", "revive_db")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "recovery_risk_data")
MODEL_PATH = str(BASE_DIR / os.getenv("MODEL_PATH", "model/recovery_risk_model.joblib"))
MODEL_VERSION = os.getenv("MODEL_VERSION", "1.0.0-prototype")


# ── Features ─────────────────────────────────────────────────

FEATURES = [
    "days_post_procedure", "age", "pain_score", "temperature_c", "heart_rate_bpm",
    "systolic_bp", "diastolic_bp", "oxygen_saturation_pct", "sleep_hours",
    "medication_adherence_pct", "exercise_adherence_pct", "daily_checkin_adherence_pct",
    "symptom_severity", "mood_score", "recovery_progress_pct", "goal_gap_count",
]
TARGET = "recovery_risk"


def clean_dataframe(documents) -> pd.DataFrame:
    rows = []
    for d in documents:
        d = dict(d)
        d.pop("_id", None)
        rows.append(d)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    for col in FEATURES:
        df[col] = pd.to_numeric(df.get(col), errors="coerce")
    return df


def make_input_frame(data: dict) -> pd.DataFrame:
    df = pd.DataFrame([data])
    for col in FEATURES:
        if col not in df:
            df[col] = np.nan
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df[FEATURES]


# ── MongoDB ──────────────────────────────────────────────────

_client: Optional[MongoClient] = None


def get_collection():
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    return _client[MONGO_DB][MONGO_COLLECTION]


def ping_mongodb() -> bool:
    get_collection().database.client.admin.command("ping")
    return True


def get_training_documents(limit=None):
    cursor = get_collection().find({})
    if limit:
        cursor = cursor.limit(int(limit))
    return list(cursor)


def get_document(document_id: str):
    from bson import ObjectId
    return get_collection().find_one({"_id": ObjectId(document_id)})


# ── Model ────────────────────────────────────────────────────

_model = None


def build_pipeline() -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", XGBClassifier(
            n_estimators=250, max_depth=4, learning_rate=0.05, subsample=0.9,
            colsample_bytree=0.9, objective="binary:logistic", eval_metric="logloss",
            random_state=42, n_jobs=4,
        )),
    ])


def train_model(documents) -> dict:
    global _model
    df = clean_dataframe(documents)
    if df.empty:
        raise ValueError("MongoDB collection is empty.")
    if TARGET not in df.columns:
        raise ValueError("Training requires a 'recovery_risk' target field (0=stable, 1=needs attention).")

    y = np.asarray(pd.to_numeric(df[TARGET], errors="coerce"))
    valid = np.isin(y, [0, 1])
    df = df.loc[valid].copy()
    y = y[valid].astype(int)
    if len(df) < 20:
        raise ValueError("At least 20 labeled records are recommended for training.")
    if len(np.unique(y)) < 2:
        raise ValueError("Training data must contain both recovery_risk=0 and recovery_risk=1.")

    X_train, X_test, y_train, y_test = train_test_split(
        df[FEATURES], y, test_size=0.2, random_state=42, stratify=y
    )
    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)

    pred = pipeline.predict(X_test)
    proba = pipeline.predict_proba(X_test)[:, 1]
    metrics = {
        "samples": int(len(df)),
        "test_samples": int(len(y_test)),
        "accuracy": float(accuracy_score(y_test, pred)),
        "precision": float(precision_score(y_test, pred, zero_division=0)),
        "recall": float(recall_score(y_test, pred, zero_division=0)),
        "f1": float(f1_score(y_test, pred, zero_division=0)),
    }
    try:
        metrics["roc_auc"] = float(roc_auc_score(y_test, proba))
    except ValueError:
        metrics["roc_auc"] = None

    Path(MODEL_PATH).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {"pipeline": pipeline, "features": FEATURES, "metrics": metrics, "model_version": MODEL_VERSION},
        MODEL_PATH,
    )
    _model = pipeline
    return metrics


def load_model() -> Pipeline:
    global _model
    if _model is None:
        if not Path(MODEL_PATH).exists():
            raise FileNotFoundError(f"Model not found at {MODEL_PATH}. Train it first.")
        _model = joblib.load(MODEL_PATH)["pipeline"]
    return _model


def risk_category(p: float) -> str:
    if p < 0.33:
        return "LOW"
    if p < 0.66:
        return "MEDIUM"
    return "HIGH"


def predict_one(frame: pd.DataFrame) -> dict:
    p = float(load_model().predict_proba(frame)[:, 1][0])
    return {
        "recovery_risk_probability": round(p, 4),
        "recovery_risk_prediction": int(p >= 0.50),
        "risk_category": risk_category(p),
    }


def explain_one(frame: pd.DataFrame) -> list[dict]:
    model = load_model()
    try:
        import shap
        # Reuse the trained imputer so all 16 features stay present, even the empty ones.
        x = model.named_steps["imputer"].transform(frame)
        values = shap.TreeExplainer(model.named_steps["model"]).shap_values(x)[0]
        pairs = [
            {"feature": f, "shap_value": float(v), "impact": "increases_risk" if v > 0 else "decreases_risk"}
            for f, v in zip(FEATURES, values)
        ]
        return sorted(pairs, key=lambda z: abs(z["shap_value"]), reverse=True)[:8]
    except Exception as exc:
        return [{"feature": "SHAP unavailable", "reason": str(exc)}]


# ── Schemas ──────────────────────────────────────────────────

class RecoveryRiskInput(BaseModel):
    days_post_procedure: Optional[float] = None
    age: Optional[float] = None
    pain_score: Optional[float] = Field(None, ge=0, le=10)
    temperature_c: Optional[float] = None
    heart_rate_bpm: Optional[float] = None
    systolic_bp: Optional[float] = None
    diastolic_bp: Optional[float] = None
    oxygen_saturation_pct: Optional[float] = None
    sleep_hours: Optional[float] = None
    medication_adherence_pct: Optional[float] = Field(None, ge=0, le=100)
    exercise_adherence_pct: Optional[float] = Field(None, ge=0, le=100)
    daily_checkin_adherence_pct: Optional[float] = Field(None, ge=0, le=100)
    symptom_severity: Optional[float] = Field(None, ge=0, le=10)
    mood_score: Optional[float] = Field(None, ge=0, le=10)
    recovery_progress_pct: Optional[float] = Field(None, ge=0, le=100)
    goal_gap_count: Optional[float] = Field(None, ge=0)


class TrainRequest(BaseModel):
    limit: Optional[int] = Field(default=None, ge=20)


class PredictionResponse(BaseModel):
    recovery_risk_probability: float
    recovery_risk_prediction: int
    risk_category: str
    shap: Optional[list[dict[str, Any]]] = None


# ── API ──────────────────────────────────────────────────────

app = FastAPI(
    title="RE:VIVE Recovery Risk AI",
    version=MODEL_VERSION,
    description="Prototype XGBoost + SHAP recovery-risk service for patient recovery monitoring.",
)


@app.get("/health")
def health():
    mongo_ok = False
    try:
        mongo_ok = ping_mongodb()
    except Exception:
        pass
    return {"status": "ok", "mongodb": mongo_ok, "model_version": MODEL_VERSION}


@app.post("/train/from-mongodb")
def train_from_mongodb(req: TrainRequest = TrainRequest()):
    try:
        metrics = train_model(get_training_documents(req.limit))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"message": "Recovery risk model trained successfully", "metrics": metrics}


@app.post("/predict", response_model=PredictionResponse)
def predict(payload: RecoveryRiskInput):
    try:
        frame = make_input_frame(payload.model_dump())
        result = predict_one(frame)
        result["shap"] = explain_one(frame)
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/predict/{document_id}", response_model=PredictionResponse)
def predict_mongodb_document(document_id: str):
    try:
        doc = get_document(document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="MongoDB document not found.")
        doc.pop("_id", None)
        frame = make_input_frame(doc)
        result = predict_one(frame)
        result["shap"] = explain_one(frame)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
