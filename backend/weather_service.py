"""
Live weather service for the Smart Library dashboard.

Fetches current and hourly weather from a configurable provider
(default: Open-Meteo), caches results, and never raises into the API layer.
"""

from __future__ import annotations

import os
import threading
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx


PROVIDER_DISPLAY_NAMES = {
    "open_meteo": "Open-Meteo",
}

# WMO weather interpretation codes (Open-Meteo / WMO)
WMO_CONDITION_MAP = {
    0: "Clear",
    1: "Mainly Clear",
    2: "Partly Cloudy",
    3: "Cloudy",
    45: "Fog",
    48: "Rime Fog",
    51: "Light Drizzle",
    53: "Drizzle",
    55: "Heavy Drizzle",
    56: "Freezing Drizzle",
    57: "Freezing Drizzle",
    61: "Light Rain",
    63: "Rain",
    65: "Heavy Rain",
    66: "Freezing Rain",
    67: "Freezing Rain",
    71: "Light Snow",
    73: "Snow",
    75: "Heavy Snow",
    77: "Snow Grains",
    80: "Light Rain",
    81: "Rain",
    82: "Heavy Rain",
    85: "Snow Showers",
    86: "Heavy Snow",
    95: "Thunderstorm",
    96: "Thunderstorm",
    99: "Thunderstorm",
}


def weather_code_to_condition(code: Optional[int]) -> str:
    if code is None:
        return "Unknown"
    return WMO_CONDITION_MAP.get(int(code), "Unknown")


def weather_code_to_category(code: Optional[int]) -> str:
    """Map a WMO code to an impact category used by the adjustment layer."""
    if code is None:
        return "UNKNOWN"
    c = int(code)
    if c == 0:
        return "CLEAR"
    if c in (1, 2):
        return "PARTLY_CLOUDY"
    if c == 3:
        return "CLOUDY"
    if c in (45, 48):
        return "CLOUDY"
    if c in (51, 53, 56, 61, 66, 80):
        return "LIGHT_RAIN"
    if c in (55, 57, 63, 67, 81):
        return "RAIN"
    if c in (65, 82):
        return "HEAVY_RAIN"
    if c in (95, 96, 99):
        return "THUNDERSTORM"
    if c in (71, 73, 75, 77, 85, 86):
        return "CLOUDY"
    return "UNKNOWN"


def _safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


class WeatherProvider(ABC):
    """Abstract weather provider so another API can be added later."""

    display_name = "Unknown"

    @abstractmethod
    def fetch(self, latitude: float, longitude: float, timezone: str) -> Dict[str, Any]:
        """Return a normalized payload with current and hourly lists."""


class OpenMeteoProvider(WeatherProvider):
    display_name = "Open-Meteo"
    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    def fetch(self, latitude: float, longitude: float, timezone: str) -> Dict[str, Any]:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone or "auto",
            "forecast_days": 2,
            "current": ",".join([
                "temperature_2m",
                "apparent_temperature",
                "precipitation",
                "rain",
                "weather_code",
                "wind_speed_10m",
            ]),
            "hourly": ",".join([
                "temperature_2m",
                "precipitation",
                "precipitation_probability",
                "rain",
                "weather_code",
                "wind_speed_10m",
            ]),
        }

        with httpx.Client(timeout=10.0) as client:
            response = client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

        current_raw = data.get("current") or {}
        hourly_raw = data.get("hourly") or {}
        times = hourly_raw.get("time") or []

        hourly: List[Dict[str, Any]] = []
        for i, time_str in enumerate(times):
            code = _safe_int(_index(hourly_raw.get("weather_code"), i))
            hourly.append({
                "time": time_str,
                "temperature": _safe_float(_index(hourly_raw.get("temperature_2m"), i)),
                "precipitation_mm": _safe_float(_index(hourly_raw.get("precipitation"), i), 0.0),
                "precipitation_probability": _safe_int(_index(hourly_raw.get("precipitation_probability"), i)),
                "rain": _safe_float(_index(hourly_raw.get("rain"), i), 0.0),
                "weather_code": code,
                "condition": weather_code_to_condition(code),
                "category": weather_code_to_category(code),
                "wind_speed": _safe_float(_index(hourly_raw.get("wind_speed_10m"), i)),
            })

        current_code = _safe_int(current_raw.get("weather_code"))
        current_time = current_raw.get("time")
        precip_prob = _precip_prob_for_time(hourly, current_time)

        current = {
            "temperature": _safe_float(current_raw.get("temperature_2m")),
            "apparent_temperature": _safe_float(current_raw.get("apparent_temperature")),
            "precipitation_mm": _safe_float(current_raw.get("precipitation"), 0.0),
            "precipitation_probability": precip_prob,
            "rain": _safe_float(current_raw.get("rain"), 0.0),
            "weather_code": current_code,
            "condition": weather_code_to_condition(current_code),
            "category": weather_code_to_category(current_code),
            "wind_speed": _safe_float(current_raw.get("wind_speed_10m")),
            "observed_at": current_time,
        }

        return {
            "current": current,
            "hourly": hourly,
            "latitude": data.get("latitude", latitude),
            "longitude": data.get("longitude", longitude),
            "timezone": data.get("timezone"),
        }


def _index(seq: Optional[List], i: int):
    if not seq or i >= len(seq):
        return None
    return seq[i]


def _precip_prob_for_time(hourly: List[Dict[str, Any]], time_str: Optional[str]) -> Optional[int]:
    if not time_str or not hourly:
        return hourly[0].get("precipitation_probability") if hourly else None
    key = str(time_str)[:13]
    for item in hourly:
        if str(item.get("time", ""))[:13] == key:
            return item.get("precipitation_probability")
    return hourly[0].get("precipitation_probability")


def create_provider(name: str) -> WeatherProvider:
    key = (name or "open_meteo").strip().lower()
    if key in ("open_meteo", "open-meteo", "openmeteo"):
        return OpenMeteoProvider()
    print(f"[Weather] Unknown provider '{name}', falling back to Open-Meteo")
    return OpenMeteoProvider()


class WeatherService:
    def __init__(
        self,
        provider: WeatherProvider,
        latitude: float,
        longitude: float,
        timezone: str,
        update_interval: int,
        provider_key: str,
    ):
        self.provider = provider
        self.latitude = latitude
        self.longitude = longitude
        self.timezone = timezone
        self.update_interval = max(60, int(update_interval))
        self.provider_key = provider_key
        self._lock = threading.Lock()
        self._cache: Optional[Dict[str, Any]] = None
        self._fetched_at: Optional[datetime] = None
        self._error: Optional[str] = None
        self._unavailable = False

    @property
    def display_name(self) -> str:
        return getattr(self.provider, "display_name", None) or PROVIDER_DISPLAY_NAMES.get(
            self.provider_key, self.provider_key
        )

    def _is_stale(self) -> bool:
        if self._cache is None or self._fetched_at is None:
            return True
        age = (datetime.now() - self._fetched_at).total_seconds()
        return age >= self.update_interval

    def refresh(self, force: bool = False) -> None:
        if not force:
            with self._lock:
                if not self._is_stale():
                    return
        try:
            payload = self.provider.fetch(self.latitude, self.longitude, self.timezone)
            with self._lock:
                self._cache = payload
                self._fetched_at = datetime.now()
                self._error = None
                self._unavailable = False
        except httpx.TimeoutException:
            self._mark_failure("Weather API timeout")
        except httpx.HTTPStatusError as exc:
            self._mark_failure(f"Weather API HTTP {exc.response.status_code}")
        except Exception as exc:
            self._mark_failure(str(exc)[:200])

    def _mark_failure(self, message: str) -> None:
        with self._lock:
            self._error = message
            if self._cache is None:
                self._unavailable = True
            print(f"[Weather] Fetch failed: {message}")

    def ensure_fresh(self) -> None:
        """Refresh only if the cache is missing or older than the update interval."""
        self.refresh(force=False)

    def get_current(self) -> Dict[str, Any]:
        self.ensure_fresh()
        with self._lock:
            if not self._cache or not self._cache.get("current"):
                return {
                    "available": False,
                    "provider": self.display_name,
                    "message": "Weather data temporarily unavailable.",
                    "error": self._error,
                    "updated_at": None,
                }

            current = dict(self._cache["current"])
            current.update({
                "available": True,
                "provider": self.display_name,
                "updated_at": self._fetched_at.isoformat() if self._fetched_at else None,
                "cached": True,
                "stale": self._error is not None,
            })
            return current

    def get_hourly(self) -> List[Dict[str, Any]]:
        self.ensure_fresh()
        with self._lock:
            if not self._cache:
                return []
            return list(self._cache.get("hourly") or [])

    def get_forecast_payload(self) -> Dict[str, Any]:
        hourly = self.get_hourly()
        with self._lock:
            available = bool(self._cache)
            updated_at = self._fetched_at.isoformat() if self._fetched_at else None
            error = self._error

        compact = []
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        for item in hourly:
            parsed = _parse_open_meteo_time(item.get("time"))
            if parsed is None or parsed < now:
                continue
            compact.append({
                "time": parsed.strftime("%H:%M"),
                "datetime": parsed.isoformat(),
                "temperature": item.get("temperature"),
                "precipitation_probability": item.get("precipitation_probability"),
                "precipitation_mm": item.get("precipitation_mm"),
                "condition": item.get("condition"),
                "category": item.get("category"),
                "weather_code": item.get("weather_code"),
                "wind_speed": item.get("wind_speed"),
                "rain": item.get("rain"),
            })
            if len(compact) >= 24:
                break

        return {
            "available": available,
            "provider": self.display_name,
            "forecast": compact,
            "updated_at": updated_at,
            "error": error,
        }

    def match_hourly(self, slot_dt: datetime) -> Optional[Dict[str, Any]]:
        key = slot_dt.strftime("%Y-%m-%dT%H")
        for item in self.get_hourly():
            if str(item.get("time", ""))[:13] == key:
                return item
        return None

    def status_summary(self) -> Dict[str, Any]:
        self.ensure_fresh()
        with self._lock:
            available = bool(self._cache)
            return {
                "enabled": True,
                "available": available,
                "provider": self.display_name,
                "updated_at": self._fetched_at.isoformat() if self._fetched_at else None,
                "error": self._error,
            }


def _parse_open_meteo_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def create_weather_service() -> Optional[WeatherService]:
    enabled = os.getenv("WEATHER_ENABLED", "false").lower() == "true"
    if not enabled:
        return None

    lat_raw = os.getenv("WEATHER_LATITUDE", "").strip()
    lon_raw = os.getenv("WEATHER_LONGITUDE", "").strip()
    if not lat_raw or not lon_raw:
        print("[Weather] Missing WEATHER_LATITUDE or WEATHER_LONGITUDE")
        return None

    try:
        latitude = float(lat_raw)
        longitude = float(lon_raw)
    except ValueError:
        print("[Weather] Invalid coordinates")
        return None

    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        print("[Weather] Coordinates out of range")
        return None

    timezone = os.getenv("WEATHER_TIMEZONE", "auto") or "auto"
    interval = int(os.getenv("WEATHER_UPDATE_INTERVAL", "900"))
    provider_key = os.getenv("WEATHER_PROVIDER", "open_meteo")
    provider = create_provider(provider_key)

    service = WeatherService(
        provider=provider,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        update_interval=interval,
        provider_key=provider_key.strip().lower(),
    )

    # Warm the cache at startup without crashing if the network is down.
    service.refresh(force=True)
    return service
