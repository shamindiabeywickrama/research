"""
Prototype weather adjustment layer.

Used only when the trained occupancy model does not include weather features.
Percentages come from environment variables and are demonstration assumptions,
not scientifically validated effects.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def load_impact_config() -> Dict[str, Any]:
    return {
        "enabled": os.getenv("WEATHER_IMPACT_ENABLED", "true").lower() == "true",
        "clear": _env_float("WEATHER_CLEAR_IMPACT", 0.0),
        "cloudy": _env_float("WEATHER_CLOUDY_IMPACT", 0.0),
        "partly_cloudy": _env_float("WEATHER_PARTLY_CLOUDY_IMPACT", 0.0),
        "rain": _env_float("WEATHER_RAIN_IMPACT", 0.10),
        "heavy_rain": _env_float("WEATHER_HEAVY_RAIN_IMPACT", 0.15),
        "thunderstorm": _env_float("WEATHER_THUNDERSTORM_IMPACT", 0.12),
        "note": (
            "Prototype weather adjustment assumptions. "
            "These factors are configurable demonstration parameters, "
            "not validated research coefficients."
        ),
    }


def model_has_weather_features(features) -> bool:
    hints = (
        "temp",
        "rain",
        "precip",
        "weather",
        "humid",
        "wind",
        "cloud",
    )
    for feature in features or []:
        name = str(feature).lower()
        if any(hint in name for hint in hints):
            return True
    return False


def factor_for_category(category: Optional[str], config: Optional[Dict[str, Any]] = None) -> float:
    cfg = config or load_impact_config()
    key = (category or "UNKNOWN").upper()
    mapping = {
        "CLEAR": cfg["clear"],
        "PARTLY_CLOUDY": cfg["partly_cloudy"],
        "CLOUDY": cfg["cloudy"],
        "LIGHT_RAIN": cfg["rain"],
        "RAIN": cfg["rain"],
        "HEAVY_RAIN": cfg["heavy_rain"],
        "THUNDERSTORM": cfg["thunderstorm"],
        "UNKNOWN": 0.0,
    }
    return float(mapping.get(key, 0.0))


def apply_adjustment(base_count: int, factor: float, capacity: int) -> int:
    adjusted = int(round(base_count * (1.0 + factor)))
    return max(0, min(int(capacity), adjusted))


def impact_label(factor: float, category: Optional[str] = None) -> str:
    if abs(factor) < 0.001:
        return "Low expected impact"
    if factor > 0:
        if factor >= 0.12:
            return "Higher indoor demand expected"
        return "Moderate increase"
    if factor <= -0.12:
        return "Lower expected demand"
    return "Moderate decrease"


def impact_reason(factor: float, condition: Optional[str]) -> str:
    label = condition or "Current weather"
    if abs(factor) < 0.001:
        return (
            f"{label}: weather may influence expected library demand, "
            "but no occupancy adjustment is applied for this condition."
        )
    direction = "increase" if factor > 0 else "reduce"
    return (
        f"Weather-adjusted estimate: {label.lower()} may {direction} "
        "expected library demand. Prototype weather impact adjustment — "
        "not a scientifically validated effect."
    )


def describe_window_weather(slots: list) -> Optional[str]:
    conditions = [
        (s.get("weather") or {}).get("condition")
        for s in slots
        if (s.get("weather") or {}).get("condition")
    ]
    if not conditions:
        return None
    return conditions[0]


def should_apply_layer(model_features, weather_available: bool) -> Tuple[bool, str]:
    """Return (apply, source_label). Never double-count weather."""
    if model_has_weather_features(model_features):
        return False, "model_weather_features"
    cfg = load_impact_config()
    if not cfg["enabled"]:
        return False, "disabled"
    if not weather_available:
        return False, "weather_unavailable"
    return True, "prototype_weather_adjustment"
