"""
Library Crowd Prediction API
-----------------------------
FastAPI backend that:
  1. Loads the trained RandomForest model (no IoT sensors involved).
  2. Exposes /predict to get occupancy % for a given date & hour context.
  3. Exposes /predict/today to get a full-day forecast (08:00-19:00).
  4. Logs every prediction into Supabase (table: predictions) for history.
  5. Exposes /history to read back stored predictions from Supabase.

Run:
    uvicorn main:app --reload --port 8000
"""

import os
import json
from datetime import datetime, date
from typing import Optional, List

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(title="Library Crowd Prediction API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Load trained model
# ---------------------------------------------------------------------------
MODEL_PATH = os.path.join(os.path.dirname(__file__), "library_crowd_model.pkl")
METRICS_PATH = os.path.join(os.path.dirname(__file__), "metrics.json")

bundle = joblib.load(MODEL_PATH)
MODEL = bundle["model"]
FEATURES = bundle["features"]

with open(METRICS_PATH) as f:
    METRICS = json.load(f)

# ---------------------------------------------------------------------------
# Supabase client (optional - app still works without it, just skips logging)
# ---------------------------------------------------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Optional[Client] = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# ---------------------------------------------------------------------------
# Helper: known exam / break weeks (mirrors dataset generator logic)
# In a real deployment this would come from an academic calendar table.
# ---------------------------------------------------------------------------
EXAM_DATE_RANGES = [
    ("2025-02-17", "2025-03-02"),
    ("2025-05-19", "2025-06-01"),
    ("2025-08-25", "2025-09-14"),
]
BREAK_DATE_RANGES = [
    ("2025-03-31", "2025-04-13"),
    ("2025-06-30", "2025-07-20"),
]


def _in_range(d: date, ranges) -> bool:
    for start, end in ranges:
        if datetime.strptime(start, "%Y-%m-%d").date() <= d <= datetime.strptime(end, "%Y-%m-%d").date():
            return True
    return False


def build_features(target_date: date, hour: int) -> pd.DataFrame:
    day_of_week = target_date.weekday()
    is_weekend = int(day_of_week >= 5)
    is_exam = int(_in_range(target_date, EXAM_DATE_RANGES))
    is_break = int(_in_range(target_date, BREAK_DATE_RANGES))

    row = {
        "hour": hour,
        "day_of_week": day_of_week,
        "is_weekend": is_weekend,
        "is_exam_period": is_exam,
        "is_semester_break": is_break,
    }
    return pd.DataFrame([row])[FEATURES]


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class PredictRequest(BaseModel):
    date: str        # "YYYY-MM-DD"
    hour: int        # 8-19


class PredictResponse(BaseModel):
    date: str
    hour: int
    predicted_occupancy_percent: float
    predicted_occupancy_count: int
    capacity: int
    is_exam_period: bool
    is_semester_break: bool
    is_weekend: bool


class DayForecastItem(BaseModel):
    hour: int
    predicted_occupancy_percent: float
    predicted_occupancy_count: int


CAPACITY = 200
OPEN_HOUR = 8
CLOSE_HOUR = 19  # inclusive last hour slot


def _predict_single(target_date: date, hour: int) -> PredictResponse:
    X = build_features(target_date, hour)
    pred_percent = float(MODEL.predict(X)[0])
    pred_percent = max(0.0, min(100.0, pred_percent))
    pred_count = int(round((pred_percent / 100) * CAPACITY))

    return PredictResponse(
        date=target_date.isoformat(),
        hour=hour,
        predicted_occupancy_percent=round(pred_percent, 1),
        predicted_occupancy_count=pred_count,
        capacity=CAPACITY,
        is_exam_period=bool(_in_range(target_date, EXAM_DATE_RANGES)),
        is_semester_break=bool(_in_range(target_date, BREAK_DATE_RANGES)),
        is_weekend=bool(target_date.weekday() >= 5),
    )


def _log_to_supabase(resp: PredictResponse):
    if not supabase:
        return
    try:
        supabase.table("predictions").insert({
            "date": resp.date,
            "hour": resp.hour,
            "predicted_occupancy_percent": resp.predicted_occupancy_percent,
            "predicted_occupancy_count": resp.predicted_occupancy_count,
            "is_exam_period": resp.is_exam_period,
            "is_semester_break": resp.is_semester_break,
            "is_weekend": resp.is_weekend,
            "created_at": datetime.utcnow().isoformat(),
        }).execute()
    except Exception as e:
        # Don't fail the request just because logging failed
        print(f"[warn] Supabase logging failed: {e}")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/")
def root():
    return {
        "message": "Library Crowd Prediction API is running",
        "model_metrics": METRICS,
        "supabase_connected": supabase is not None,
    }


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    try:
        target_date = datetime.strptime(req.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be in YYYY-MM-DD format")

    if not (OPEN_HOUR <= req.hour <= CLOSE_HOUR):
        raise HTTPException(status_code=400, detail=f"hour must be between {OPEN_HOUR} and {CLOSE_HOUR}")

    resp = _predict_single(target_date, req.hour)
    _log_to_supabase(resp)
    return resp


@app.get("/predict/day", response_model=List[DayForecastItem])
def predict_day(date_str: str):
    """Full-day forecast for hours 08:00-19:00. Query param: ?date_str=YYYY-MM-DD"""
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="date_str must be in YYYY-MM-DD format")

    results = []
    for hour in range(OPEN_HOUR, CLOSE_HOUR + 1):
        resp = _predict_single(target_date, hour)
        _log_to_supabase(resp)
        results.append(DayForecastItem(
            hour=hour,
            predicted_occupancy_percent=resp.predicted_occupancy_percent,
            predicted_occupancy_count=resp.predicted_occupancy_count,
        ))
    return results


@app.get("/history")
def get_history(limit: int = 50):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase is not configured on this server")
    try:
        result = supabase.table("predictions").select("*").order("created_at", desc=True).limit(limit).execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics")
def get_metrics():
    return METRICS
