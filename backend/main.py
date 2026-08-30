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
import asyncio
from datetime import datetime, date, timedelta
from typing import Optional, List
from contextlib import asynccontextmanager

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from supabase import create_client, Client

from wifi_monitor import create_wifi_monitor
from weather_service import create_weather_service
from weather_impact import (
    apply_adjustment,
    describe_window_weather,
    factor_for_category,
    impact_label,
    impact_reason,
    load_impact_config,
    model_has_weather_features,
    should_apply_layer,
)

load_dotenv()

# ---------------------------------------------------------------------------
# Wi-Fi Monitor Setup
# ---------------------------------------------------------------------------
wifi_monitor = create_wifi_monitor()
wifi_websocket_clients: List[WebSocket] = []
_main_loop: Optional[asyncio.AbstractEventLoop] = None

# ---------------------------------------------------------------------------
# Weather Service Setup
# ---------------------------------------------------------------------------
weather_service = create_weather_service()


def wifi_websocket_callback(status: dict):
    """Broadcast Wi-Fi updates from the monitor thread onto the FastAPI event loop."""
    loop = _main_loop
    if loop is None or not loop.is_running():
        return
    asyncio.run_coroutine_threadsafe(_broadcast_wifi_update(status), loop)


async def _broadcast_wifi_update(status: dict):
    """Broadcast Wi-Fi status update to all connected clients."""
    disconnected = []
    for client in list(wifi_websocket_clients):
        try:
            await client.send_json(status)
        except Exception:
            disconnected.append(client)
    for client in disconnected:
        if client in wifi_websocket_clients:
            wifi_websocket_clients.remove(client)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - startup and shutdown events."""
    global _main_loop
    _main_loop = asyncio.get_running_loop()
    if wifi_monitor:
        wifi_monitor.set_websocket_callback(wifi_websocket_callback)
        wifi_monitor.start()
        print("\n" + "="*50)
        print("Wi-Fi Monitor")
        print("="*50)
        print(f"Interface IP: {wifi_monitor.interface_ip}")
        print(f"Gateway: {wifi_monitor.gateway}")
        print(f"Subnet: {wifi_monitor.subnet}")
        print(f"Scan interval: {wifi_monitor.scan_interval} seconds")
        print(f"Excluded devices: {len(wifi_monitor.exclude_ips)}")
        print(f"Baseline occupancy: {wifi_monitor.baseline}")
        print(f"Status: ACTIVE")
        print("="*50 + "\n")
    if weather_service:
        status = weather_service.status_summary()
        print("\n" + "="*50)
        print("Weather Service")
        print("="*50)
        print(f"Provider: {weather_service.display_name}")
        print(f"Latitude: {weather_service.latitude}")
        print(f"Longitude: {weather_service.longitude}")
        print(f"Update interval: {weather_service.update_interval} seconds")
        print(f"Available: {status['available']}")
        print("="*50 + "\n")
    yield
    # Shutdown
    if wifi_monitor:
        wifi_monitor.stop()


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(title="Library Crowd Prediction API", version="2.0.0", lifespan=lifespan)

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
WIFI_DATA_MODES = {"wifi", "wifi_weather"}
CAPACITY = int(os.getenv("LIBRARY_CAPACITY", "200"))
OPEN_HOUR = int(os.getenv("LIBRARY_OPEN_HOUR", "8"))
CLOSE_HOUR = int(os.getenv("LIBRARY_CLOSE_HOUR", "19"))

MODEL_PATH = os.path.join(os.path.dirname(__file__), "library_crowd_model.pkl")
METRICS_PATH = os.path.join(os.path.dirname(__file__), "metrics.json")

bundle = joblib.load(MODEL_PATH)
MODEL = bundle["model"]
FEATURES = bundle["features"]
MODEL_USES_WEATHER = model_has_weather_features(FEATURES)

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


def _wifi_live_occupancy_enabled() -> bool:
    return DATA_MODE in WIFI_DATA_MODES and wifi_monitor is not None


def _weather_payload_compact(hourly_item: Optional[dict]) -> Optional[dict]:
    if not hourly_item:
        return None
    return {
        "temperature": hourly_item.get("temperature"),
        "rain_probability": hourly_item.get("precipitation_probability"),
        "precipitation_probability": hourly_item.get("precipitation_probability"),
        "precipitation_mm": hourly_item.get("precipitation_mm"),
        "rain": hourly_item.get("rain"),
        "condition": hourly_item.get("condition"),
        "category": hourly_item.get("category"),
        "wind_speed": hourly_item.get("wind_speed"),
    }


def _apply_weather_to_forecast(forecast: List[dict]) -> List[dict]:
    """Attach weather and optional prototype adjustment. Never double-count weather."""
    weather_available = bool(weather_service and weather_service.get_hourly())
    apply_layer, source = should_apply_layer(FEATURES, weather_available)
    impact_cfg = load_impact_config()

    for slot in forecast:
        base = int(slot["predicted_occupancy"])
        slot["base_prediction"] = base
        slot["weather"] = None
        slot["weather_adjustment"] = 0.0
        slot["weather_adjusted_prediction"] = base
        slot["adjustment_source"] = source

        if not weather_service:
            continue

        try:
            slot_dt = datetime.fromisoformat(slot["datetime"])
            matched = weather_service.match_hourly(slot_dt)
        except Exception:
            matched = None

        weather = _weather_payload_compact(matched)
        slot["weather"] = weather

        if not apply_layer or not weather or not slot.get("is_open"):
            continue

        factor = factor_for_category(weather.get("category"), impact_cfg)
        adjusted = apply_adjustment(base, factor, CAPACITY)
        percentage = round((adjusted / CAPACITY) * 100, 1) if CAPACITY else 0.0
        slot["weather_adjustment"] = factor
        slot["weather_adjusted_prediction"] = adjusted
        slot["predicted_occupancy"] = adjusted
        slot["percentage"] = percentage
        slot["status"] = _occupancy_status(percentage, True)

    return forecast


def _weather_insight_from_current() -> Optional[dict]:
    if not weather_service:
        return None
    current = weather_service.get_current()
    if not current.get("available"):
        return {
            "available": False,
            "message": "Weather data temporarily unavailable.",
        }

    apply_layer, source = should_apply_layer(FEATURES, True)
    factor = 0.0
    if apply_layer:
        factor = factor_for_category(current.get("category"))

    return {
        "available": True,
        "condition": current.get("condition"),
        "temperature": current.get("temperature"),
        "precipitation_probability": current.get("precipitation_probability"),
        "impact_label": impact_label(factor, current.get("category")),
        "impact_factor": factor,
        "reason": impact_reason(factor, current.get("condition")),
        "adjustment_source": source,
        "prototype": source == "prototype_weather_adjustment",
    }


def _log_weather_to_supabase(slot: dict):
    if not supabase:
        return
    weather = slot.get("weather") or {}
    try:
        supabase.table("weather_prediction_logs").insert({
            "timestamp": slot.get("datetime"),
            "temperature": weather.get("temperature"),
            "precipitation": weather.get("precipitation_mm"),
            "rain_probability": weather.get("rain_probability"),
            "weather_condition": weather.get("condition"),
            "base_prediction": slot.get("base_prediction"),
            "weather_adjusted_prediction": slot.get("weather_adjusted_prediction"),
        }).execute()
    except Exception as e:
        print(f"[warn] Weather Supabase logging failed: {e}")


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

    return _apply_weather_to_forecast(forecast)


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

        weather_condition = describe_window_weather(chunk)
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
            "weather": weather_condition,
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
        "weather_enabled": weather_service is not None,
        "weather_available": bool(weather_service and weather_service.status_summary().get("available")),
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/library/current")
def api_current_occupancy():
    now = datetime.now()
    hour = now.hour
    target_date = now.date()

    # Use Wi-Fi simulation when DATA_MODE is wifi or wifi_weather
    if _wifi_live_occupancy_enabled():
        wifi_status = wifi_monitor.get_status()
        occupied = wifi_status["occupancy_count"]
        percentage = (occupied / CAPACITY) * 100 if CAPACITY > 0 else 0
        status = _occupancy_status(percentage, _is_library_open(hour))

        return {
            "capacity": CAPACITY,
            "occupied": occupied,
            "occupancy_percentage": round(percentage, 1),
            "status": status,
            "available_seats": max(0, CAPACITY - occupied),
            "updated_at": now.isoformat(),
            "data_mode": DATA_MODE,
            "is_open": _is_library_open(hour),
            "wifi_detected_devices": wifi_status["detected_devices"],
            "wifi_baseline": wifi_status["baseline"],
            "is_exam_period": bool(_in_range(target_date, EXAM_DATE_RANGES)),
            "is_semester_break": bool(_in_range(target_date, BREAK_DATE_RANGES)),
            "is_weekend": bool(target_date.weekday() >= 5),
        }

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
    apply_layer, source = should_apply_layer(
        FEATURES,
        bool(weather_service and weather_service.get_hourly()),
    )
    if supabase and apply_layer:
        current_hour = forecast[0] if forecast else None
        if current_hour:
            _log_weather_to_supabase(current_hour)
    return {
        "forecast": forecast,
        "data_mode": DATA_MODE,
        "generated_at": datetime.now().isoformat(),
        "insights": _compute_quick_insights(forecast),
        "weather_insight": _weather_insight_from_current(),
        "model_uses_weather_features": MODEL_USES_WEATHER,
        "weather_adjustment_source": source,
        "weather_adjustment_enabled": apply_layer,
        "weather_adjustment_note": (
            "Weather-adjusted estimate using prototype weather impact adjustment. "
            "The trained model does not include weather features."
            if apply_layer
            else (
                "Weather is already represented in the trained model; no separate adjustment is applied."
                if source == "model_weather_features"
                else "Weather adjustment is not applied."
            )
        ),
    }


@app.get("/api/library/recommendations")
def api_recommendations():
    forecast = _build_24h_forecast()
    windows = _find_best_windows(forecast, window_hours=2, count=2)
    apply_layer, source = should_apply_layer(
        FEATURES,
        bool(weather_service and weather_service.get_hourly()),
    )
    return {
        "recommendations": windows,
        "data_mode": DATA_MODE,
        "generated_at": datetime.now().isoformat(),
        "uses_weather_adjusted_forecast": apply_layer,
        "weather_adjustment_source": source,
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
    wifi_live = _wifi_live_occupancy_enabled()
    wifi_status = "Active" if wifi_live else "Planned"
    wifi_desc = (
        "Local network device simulation"
        if wifi_live
        else "Live device counts from campus Wi-Fi"
    )

    if weather_service:
        wx = weather_service.status_summary()
        weather_status = "Connected" if wx.get("available") else "Unavailable"
        weather_desc = f"Live weather powered by {weather_service.display_name}"
    else:
        weather_status = "Planned"
        weather_desc = "Weather API integration is not enabled"

    return {
        "sources": [
            {
                "id": "wifi",
                "name": "Wi-Fi Device Data",
                "status": wifi_status,
                "description": wifi_desc,
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
                "name": "Live Weather",
                "status": weather_status,
                "description": weather_desc,
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


@app.get("/api/weather/current")
def api_weather_current():
    if not weather_service:
        return {
            "available": False,
            "provider": None,
            "message": "Weather data temporarily unavailable.",
        }
    payload = weather_service.get_current()
    insight = _weather_insight_from_current()
    payload["impact"] = insight
    payload["model_uses_weather_features"] = MODEL_USES_WEATHER
    return payload


@app.get("/api/weather/forecast")
def api_weather_forecast():
    if not weather_service:
        return {
            "available": False,
            "provider": None,
            "forecast": [],
            "message": "Weather data temporarily unavailable.",
        }
    return weather_service.get_forecast_payload()


@app.get("/api/network/status")
def api_network_status():
    """Get current Wi-Fi network monitoring status."""
    if not wifi_monitor:
        return {
            "enabled": False,
            "mode": "none",
            "message": "Wi-Fi simulation is not enabled",
        }
    
    return wifi_monitor.get_status()


@app.get("/api/network/events")
def api_network_events():
    """Get recent device connection/disconnection events."""
    if not wifi_monitor:
        return {"events": []}
    
    return {"events": wifi_monitor.get_events()}


@app.websocket("/ws/network")
async def websocket_network(websocket: WebSocket):
    """WebSocket endpoint for real-time network status updates."""
    await websocket.accept()
    wifi_websocket_clients.append(websocket)
    
    try:
        # Send initial status
        if wifi_monitor:
            await websocket.send_json(wifi_monitor.get_status())
        
        # Keep connection alive
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        wifi_websocket_clients.remove(websocket)
    except Exception:
        if websocket in wifi_websocket_clients:
            wifi_websocket_clients.remove(websocket)
