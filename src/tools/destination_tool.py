import json
from pathlib import Path
from typing import List

CITY_ALIASES = {
    "da nang": "Đà Nẵng",
    "danang": "Đà Nẵng",
    "hanoi": "Hà Nội",
    "ha noi": "Hà Nội",
    "hoi an": "Hội An",
    "hoian": "Hội An",
}

STYLE_MAP = {
    "nghỉ dưỡng": "nghỉ dưỡng",
    "nghi duong": "nghỉ dưỡng",
    "resort": "nghỉ dưỡng",
    "relax": "nghỉ dưỡng",
    "ẩm thực": "ẩm thực",
    "am thuc": "ẩm thực",
    "culinary": "ẩm thực",
    "food": "ẩm thực",
    "khám phá": "khám phá",
    "kham pha": "khám phá",
    "explore": "khám phá",
    "adventure": "khám phá",
}


def _normalize_text(value: str) -> str:
    return value.strip().lower()


def _normalize_city(value: str) -> str:
    normalized = _normalize_text(value)
    return CITY_ALIASES.get(normalized, value.strip())


def _normalize_style(value: str) -> str:
    normalized = _normalize_text(value)
    return STYLE_MAP.get(normalized, value.strip())


def _load_destinations() -> dict:
    root = Path(__file__).resolve().parents[2]
    data_path = root / "data" / "destinations.json"
    if not data_path.exists():
        raise FileNotFoundError(f"Destination data file not found: {data_path}")

    with data_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _format_destination(destination: dict) -> str:
    name = destination.get("name", "Unknown địa điểm")
    description = destination.get("description", "")
    return f"- {name}: {description}" if description else f"- {name}"


def search_destinations(city: str, travel_style: str) -> str:
    """Tra cứu địa điểm du lịch theo thành phố và phong cách (nghỉ dưỡng/ẩm thực/khám phá)"""
    city_key = _normalize_city(city)
    style_key = _normalize_style(travel_style)

    try:
        destinations = _load_destinations()
    except FileNotFoundError as exc:
        return str(exc)

    city_options = {name.lower(): name for name in destinations.keys()}
    normalized_city_key = city_key.lower()
    city_name = city_options.get(normalized_city_key) or city_key

    if city_name not in destinations:
        available = ", ".join(sorted(destinations.keys()))
        return (
            f"Không tìm thấy dữ liệu cho thành phố '{city}'. "
            f"Các thành phố hiện có: {available}."
        )

    city_destinations = destinations[city_name]
    filtered = [d for d in city_destinations if _normalize_style(d.get("style", "")) == style_key]

    if not filtered:
        return (
            f"Không tìm thấy địa điểm phù hợp cho thành phố '{city_name}' với phong cách '{travel_style}'. "
            f"Vui lòng thử lại với một trong các phong cách: nghỉ dưỡng, ẩm thực, khám phá."
        )

    header = f"Địa điểm ở {city_name} phù hợp với phong cách '{style_key}':"
    formatted = "\n".join(_format_destination(dest) for dest in filtered)
    return f"{header}\n{formatted}"
