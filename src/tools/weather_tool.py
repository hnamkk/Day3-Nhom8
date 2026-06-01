import json
from pathlib import Path
from typing import Dict

CITY_ALIASES = {
    "da nang": "Đà Nẵng",
    "danang": "Đà Nẵng",
    "hanoi": "Hà Nội",
    "ha noi": "Hà Nội",
    "hoi an": "Hội An",
    "hoian": "Hội An",
}


def _normalize_text(value: str) -> str:
    return value.strip().lower()


def _normalize_city(value: str) -> str:
    normalized = _normalize_text(value)
    return CITY_ALIASES.get(normalized, value.strip())


def _load_weather_data() -> dict:
    root = Path(__file__).resolve().parents[2]
    data_path = root / "data" / "weather_forecasts.json"
    if not data_path.exists():
        raise FileNotFoundError(f"Weather data file not found: {data_path}")

    with data_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _format_day_summary(date: str, temp_c: float, description: str) -> str:
    return f"{date}: {temp_c:.1f}°C, {description}"


def get_weather_forecast(city: str) -> str:
    """Lấy dự báo thời tiết 3 ngày tới cho thành phố"""
    city_name = _normalize_city(city)

    try:
        forecast_data = _load_weather_data()
    except FileNotFoundError as exc:
        return str(exc)

    available_cities = {name.lower(): name for name in forecast_data.keys()}
    selected_city = available_cities.get(city_name.lower(), city_name)

    if selected_city not in forecast_data:
        available = ", ".join(sorted(forecast_data.keys()))
        return (
            f"Không tìm thấy dữ liệu thời tiết cho thành phố '{city}'. "
            f"Các thành phố hiện có: {available}."
        )

    forecasts = forecast_data[selected_city]
    lines = [
        _format_day_summary(day["date"], day["temp_c"], day["description"])
        for day in forecasts[:3]
    ]
    return f"Dự báo thời tiết 3 ngày cho {selected_city}:\n" + "\n".join(lines)
