import json
import os
from typing import Optional

# Resolve the path to data/hotels.json relative to this file's location
_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "hotels.json")

# City name aliases so the agent can use common names
_CITY_ALIASES = {
    "đà nẵng": "da_nang",
    "da nang": "da_nang",
    "danang": "da_nang",
    "hà nội": "ha_noi",
    "ha noi": "ha_noi",
    "hanoi": "ha_noi",
    "hội an": "hoi_an",
    "hoi an": "hoi_an",
    "hoian": "hoi_an",
}


def _load_hotels() -> dict:
    """Load hotel data from the JSON database."""
    abs_path = os.path.abspath(_DATA_PATH)
    with open(abs_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _normalize_city(city: str) -> Optional[str]:
    """Normalize city name to a database key."""
    key = city.strip().lower()
    # Direct key match
    data = _load_hotels()
    if key in data["hotels"]:
        return key
    # Alias lookup
    return _CITY_ALIASES.get(key)


def check_hotel_prices(city: str, budget_per_night: int) -> str:
    """Tìm khách sạn phù hợp ngân sách mỗi đêm (VND).

    Args:
        city: Tên thành phố (Đà Nẵng, Hà Nội, Hội An).
        budget_per_night: Ngân sách tối đa mỗi đêm tính theo VND.

    Returns:
        Chuỗi văn bản mô tả top 3 khách sạn phù hợp.
    """
    city_key = _normalize_city(city)
    if city_key is None:
        return (
            f"Không tìm thấy dữ liệu khách sạn cho thành phố '{city}'. "
            "Hiện hệ thống hỗ trợ: Đà Nẵng, Hà Nội, Hội An."
        )

    data = _load_hotels()
    hotels = data["hotels"][city_key]

    # Filter hotels within budget
    affordable = [h for h in hotels if h["price_per_night"] <= budget_per_night]

    if not affordable:
        cheapest = min(hotels, key=lambda h: h["price_per_night"])
        return (
            f"Không tìm thấy khách sạn tại {city} trong ngân sách "
            f"{budget_per_night:,} VND/đêm.\n"
            f"Khách sạn rẻ nhất hiện có: {cheapest['name']} "
            f"({cheapest['price_per_night']:,} VND/đêm, {cheapest['stars']}⭐)."
        )

    # Sort by rating descending, take top 3
    top3 = sorted(affordable, key=lambda h: h["rating"], reverse=True)[:3]

    lines = [
        f"🏨 Top {len(top3)} khách sạn tại {city} trong ngân sách "
        f"{budget_per_night:,} VND/đêm:\n"
    ]
    for i, hotel in enumerate(top3, start=1):
        amenities_str = ", ".join(hotel["amenities"][:3])
        lines.append(
            f"{i}. **{hotel['name']}** ({hotel['stars']}⭐ | ⭐ Đánh giá: {hotel['rating']}/5)\n"
            f"   - Giá: {hotel['price_per_night']:,} VND/đêm\n"
            f"   - Vị trí: {hotel['location']}\n"
            f"   - Tiện nghi nổi bật: {amenities_str}\n"
            f"   - Địa chỉ: {hotel['address']}\n"
        )

    return "\n".join(lines)
