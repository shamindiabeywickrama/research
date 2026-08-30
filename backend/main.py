"""
Library Crowd Prediction API
-----------------------------
FastAPI backend that:
  1. Loads the trained RandomForest model (no IoT sensors involved).
  2. Exposes legacy /predict and /predict/day endpoints.
  3. Exposes /api/library/* endpoints for the Smart Library dashboard.
  4. Logs predictions into Supabase when configured.

Run:
    uvicorn main:app --reload --port 8000
"""

import os
import json
from datetime import datetime, date, timedelta
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
app = FastAPI(title="Library Crowd Prediction API", version="2.0.0")

CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in CORS_ORIGINS if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DATA_MODE = os.getenv("DATA_MODE", "demo").lower()
CAPACITY = int(os.getenv("LIBRARY_CAPACITY", "200"))
OPEN_HOUR = int(os.getenv("LIBRARY_OPEN_HOUR", "8"))
CLOSE_HOUR = int(os.getenv("LIBRARY_CLOSE_HOUR", "19"))

MODEL_PATH = os.path.join(os.path.dirname(__file__), "library_crowd_model.pkl")
METRICS_PATH = os.path.join(os.path.dirname(__file__), "metrics.json")

bundle = joblib.load(MODEL_PATH)
MODEL = bundle["model"]
FEATURES = bundle["features"]

with open(METRICS_PATH) as f:
    METRICS = json.load(f)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Optional[Client] = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

EXAM_DATE_RANGES = [
    ("2025-02-17", "2025-03-02"),
    ("2025-05-19", "2025-06-01"),
    ("2025-08-25", "2025-09-14"),
]
BREAK_DATE_RANGES = [
    ("2025-03-31", "2025-04-13"),
    ("2025-06-30", "2025-07-20"),
]

# Status thresholds (occupancy percentage)
LOW_THRESHOLD = 40.0
HIGH_THRESHOLD = 65.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
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


def _occupancy_status(percent: float, is_open: bool = True) -> str:
    if not is_open:
        return "Closed"
    if percent < LOW_THRESHOLD:
        return "Low"
    if percent < HIGH_THRESHOLD:
        return "Moderate"
    return "High"


def _format_time_12h(hour: int) -> str:
    period = "AM" if hour < 12 else "PM"
    hr12 = hour % 12 or 12
    return f"{hr12:02d}:00 {period}"


def _format_time_24h(hour: int) -> str:
    return f"{hour:02d}:00"


def _is_library_open(hour: int) -> bool:
    return OPEN_HOUR <= hour <= CLOSE_HOUR


def _predict_single(target_date: date, hour: int) -> dict:
    if not _is_library_open(hour):
        return {
            "date": target_date.isoformat(),
            "hour": hour,
            "predicted_occupancy_percent": 0.0,
            "predicted_occupancy_count": 0,
            "capacity": CAPACITY,
            "percentage": 0.0,
            "status": "Closed",
            "is_open": False,
            "is_exam_period": bool(_in_range(target_date, EXAM_DATE_RANGES)),
            "is_semester_break": bool(_in_range(target_date, BREAK_DATE_RANGES)),
            "is_weekend": bool(target_date.weekday() >= 5),
        }

    X = build_features(target_date, hour)
    pred_percent = float(MODEL.predict(X)[0])
    pred_percent = max(0.0, min(100.0, pred_percent))
    pred_count = int(round((pred_percent / 100) * CAPACITY))

    return {
        "date": target_date.isoformat(),
        "hour": hour,
        "predicted_occupancy_percent": round(pred_percent, 1),
        "predicted_occupancy_count": pred_count,
        "capacity": CAPACITY,
        "percentage": round(pred_percent, 1),
        "status": _occupancy_status(pred_percent),
        "is_open": True,
        "is_exam_period": bool(_in_range(target_date, EXAM_DATE_RANGES)),
        "is_semester_break": bool(_in_range(target_date, BREAK_DATE_RANGES)),
        "is_weekend": bool(target_date.weekday() >= 5),
    }


def _build_24h_forecast(from_dt: Optional[datetime] = None) -> List[dict]:
    """Rolling 24-hour forecast starting from the current hour."""
    now = from_dt or datetime.now()
    start = now.replace(minute=0, second=0, microsecond=0)
    forecast = []

    for i in range(24):
        slot = start + timedelta(hours=i)
        target_date = slot.date()
        hour = slot.hour
        pred = _predict_single(target_date, hour)
        forecast.append({
            "time": _format_time_24h(hour),
            "datetime": slot.isoformat(),
            "hour": hour,
            "predicted_occupancy": pred["predicted_occupancy_count"],
            "capacity": CAPACITY,
            "percentage": pred["percentage"],
            "status": pred["status"],
            "is_open": pred["is_open"],
        })

    return forecast


def _find_best_windows(forecast: List[dict], window_hours: int = 2, count: int = 2) -> List[dict]:
    """Find the lowest-average-occupancy 2-hour windows during open hours."""
    if len(forecast) < window_hours:
        return []

    windows = []
    for i in range(len(forecast) - window_hours + 1):
        chunk = forecast[i : i + window_hours]
        if not all(s["is_open"] for s in chunk):
            continue

        consecutive = True
        for j in range(1, len(chunk)):
            t1 = datetime.fromisoformat(chunk[j - 1]["datetime"])
            t2 = datetime.fromisoformat(chunk[j]["datetime"])
            if (t2 - t1) != timedelta(hours=1):
                consecutive = False
                break
        if not consecutive:
            continue

        avg_occ = sum(s["predicted_occupancy"] for s in chunk) / window_hours
        start_hour = chunk[0]["hour"]
        end_hour = chunk[-1]["hour"] + 1
        if end_hour == 24:
            end_hour = 0

        windows.append({
            "start_time": _format_time_12h(start_hour),
            "end_time": _format_time_12h(end_hour),
            "start_hour": start_hour,
            "end_hour": end_hour,
            "start_datetime": chunk[0]["datetime"],
            "end_datetime": chunk[-1]["datetime"],
            "estimated_occupancy": int(round(avg_occ)),
            "crowd_level": _occupancy_status((avg_occ / CAPACITY) * 100),
            "average_percentage": round((avg_occ / CAPACITY) * 100, 1),
        })

    windows.sort(key=lambda w: w["estimated_occupancy"])

    selected = []
    used_ranges = []
    for window in windows:
        start_dt = datetime.fromisoformat(window["start_datetime"])
        end_dt = datetime.fromisoformat(window["end_datetime"]) + timedelta(hours=1)
        overlaps = any(
            start_dt < used_end and end_dt > used_start
            for used_start, used_end in used_ranges
        )
        if overlaps:
            continue
        selected.append({k: v for k, v in window.items() if not k.endswith("_datetime")})
        used_ranges.append((start_dt, end_dt))
        if len(selected) >= count:
            break

    return selected


def _compute_quick_insights(forecast: List[dict]) -> dict:
    open_slots = [f for f in forecast if f["is_open"]]
    if not open_slots:
        return {
            "today_average": 0,
            "today_peak": 0,
            "quietest_period": "—",
            "available_seats": CAPACITY,
        }

    occupancies = [s["predicted_occupancy"] for s in open_slots]
    avg = int(round(sum(occupancies) / len(occupancies)))
    peak = max(occupancies)
    quietest = min(open_slots, key=lambda s: s["predicted_occupancy"])
    current = open_slots[0] if open_slots else {"predicted_occupancy": 0}

    return {
        "today_average": avg,
        "today_peak": peak,
        "quietest_period": quietest["time"],
        "available_seats": max(0, CAPACITY - current["predicted_occupancy"]),
    }


def _log_to_supabase(resp: dict):
    if not supabase:
        return
    try:
        supabase.table("predictions").insert({
            "date": resp["date"],
            "hour": resp["hour"],
            "predicted_occupancy_percent": resp["predicted_occupancy_percent"],
            "predicted_occupancy_count": resp["predicted_occupancy_count"],
            "is_exam_period": resp["is_exam_period"],
            "is_semester_break": resp["is_semester_break"],
            "is_weekend": resp["is_weekend"],
            "created_at": datetime.utcnow().isoformat(),
        }).execute()
    except Exception as e:
        print(f"[warn] Supabase logging failed: {e}")


# ---------------------------------------------------------------------------
# Legacy schemas (backward compatible)
# ---------------------------------------------------------------------------
class PredictRequest(BaseModel):
    date: str
    hour: int


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


def _to_legacy_response(pred: dict) -> PredictResponse:
    return PredictResponse(
        date=pred["date"],
        hour=pred["hour"],
        predicted_occupancy_percent=pred["predicted_occupancy_percent"],
        predicted_occupancy_count=pred["predicted_occupancy_count"],
        capacity=pred["capacity"],
        is_exam_period=pred["is_exam_period"],
        is_semester_break=pred["is_semester_break"],
        is_weekend=pred["is_weekend"],
    )


# ---------------------------------------------------------------------------
# Legacy routes
# ---------------------------------------------------------------------------
@app.get("/")
def root():
    return {
        "message": "Library Crowd Prediction API is running",
        "model_metrics": METRICS,
        "supabase_connected": supabase is not None,
        "data_mode": DATA_MODE,
    }


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    try:
        target_date = datetime.strptime(req.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be in YYYY-MM-DD format")

    if not (OPEN_HOUR <= req.hour <= CLOSE_HOUR):
        raise HTTPException(
            status_code=400,
            detail=f"hour must be between {OPEN_HOUR} and {CLOSE_HOUR}",
        )

    pred = _predict_single(target_date, req.hour)
    resp = _to_legacy_response(pred)
    _log_to_supabase(pred)
    return resp


@app.get("/predict/day", response_model=List[DayForecastItem])
def predict_day(date_str: str):
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="date_str must be in YYYY-MM-DD format")

    results = []
    for hour in range(OPEN_HOUR, CLOSE_HOUR + 1):
        pred = _predict_single(target_date, hour)
        _log_to_supabase(pred)
        results.append(DayForecastItem(
            hour=hour,
            predicted_occupancy_percent=pred["predicted_occupancy_percent"],
            predicted_occupancy_count=pred["predicted_occupancy_count"],
        ))
    return results


@app.get("/history")
def get_history(limit: int = 50):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase is not configured on this server")
    try:
        result = (
            supabase.table("predictions")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics")
def get_metrics_legacy():
    return METRICS


# ---------------------------------------------------------------------------
# Smart Library Dashboard API
# ---------------------------------------------------------------------------
@app.get("/api/health")
def api_health():
    return {
        "status": "online",
        "data_mode": DATA_MODE,
        "model_loaded": MODEL is not None,
        "supabase_connected": supabase is not None,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/library/current")
def api_current_occupancy():
    now = datetime.now()
    hour = now.hour
    target_date = now.date()

    if not _is_library_open(hour):
        nearest_hour = OPEN_HOUR if hour < OPEN_HOUR else CLOSE_HOUR
        pred = _predict_single(target_date, nearest_hour)
        return {
            "capacity": CAPACITY,
            "occupied": 0,
            "occupancy_percentage": 0.0,
            "status": "Closed",
            "available_seats": CAPACITY,
            "updated_at": now.isoformat(),
            "data_mode": DATA_MODE,
            "is_open": False,
            "message": f"Library is currently closed. Open hours: {OPEN_HOUR:02d}:00–{CLOSE_HOUR:02d}:00",
            "next_open_prediction": pred,
        }

    pred = _predict_single(target_date, hour)
    occupied = pred["predicted_occupancy_count"]
    percentage = pred["percentage"]
    status = pred["status"]

    return {
        "capacity": CAPACITY,
        "occupied": occupied,
        "occupancy_percentage": percentage,
        "status": status,
        "available_seats": max(0, CAPACITY - occupied),
        "updated_at": now.isoformat(),
        "data_mode": DATA_MODE,
        "is_open": True,
        "is_exam_period": pred["is_exam_period"],
        "is_semester_break": pred["is_semester_break"],
        "is_weekend": pred["is_weekend"],
    }


@app.get("/api/library/forecast")
def api_forecast():
    forecast = _build_24h_forecast()
    return {
        "forecast": forecast,
        "data_mode": DATA_MODE,
        "generated_at": datetime.now().isoformat(),
        "insights": _compute_quick_insights(forecast),
    }


@app.get("/api/library/recommendations")
def api_recommendations():
    forecast = _build_24h_forecast()
    windows = _find_best_windows(forecast, window_hours=2, count=2)
    return {
        "recommendations": windows,
        "data_mode": DATA_MODE,
        "generated_at": datetime.now().isoformat(),
    }


@app.get("/api/library/metrics")
def api_metrics():
    display_metrics = {}
    label_map = {
        "mae": "MAE",
        "r2_score": "R² Score",
        "mape": "MAPE",
        "rmse": "RMSE",
        "accuracy": "Accuracy",
        "recall": "Recall",
    }
    for key, label in label_map.items():
        if key in METRICS:
            display_metrics[label] = METRICS[key]

    return {
        "metrics": display_metrics,
        "raw": METRICS,
        "note": "Based on evaluation data",
    }


@app.get("/api/library/data-sources")
def api_data_sources():
    return {
        "sources": [
            {
                "id": "wifi",
                "name": "Wi-Fi Device Data",
                "status": "Planned",
                "description": "Live device counts from campus Wi-Fi (not yet integrated)",
            },
            {
                "id": "calendar",
                "name": "Academic Calendar",
                "status": "Demo",
                "description": "Hardcoded semester and exam date ranges",
            },
            {
                "id": "exams",
                "name": "Exam Schedule",
                "status": "Demo",
                "description": "Exam period flags derived from configured date ranges",
            },
            {
                "id": "weather",
                "name": "Weather Data",
                "status": "Planned",
                "description": "Weather API integration planned for future work",
            },
            {
                "id": "historical",
                "name": "Historical Occupancy",
                "status": "Demo",
                "description": "Synthetic dataset used to train the RandomForest model",
            },
        ],
        "data_mode": DATA_MODE,
    }
