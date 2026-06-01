TRAVEL_TOOLS = [
    {
        "name": "get_weather_forecast",
        "description": "Lấy dự báo thời tiết 3 ngày tới cho một thành phố. Args JSON: {\"city\": \"Đà Nẵng\"}",
    },
    {
        "name": "search_destinations",
        "description": (
            "Tra cứu địa điểm du lịch theo thành phố và phong cách. "
            "Args JSON: {\"city\": \"Đà Nẵng\", \"travel_style\": \"nghỉ dưỡng|ẩm thực|khám phá\"}"
        ),
    },
    {
        "name": "check_hotel_prices",
        "description": (
            "Tìm khách sạn phù hợp ngân sách mỗi đêm theo VND. "
            "Args JSON: {\"city\": \"Đà Nẵng\", \"budget_per_night\": 800000}"
        ),
    },
    {
        "name": "calculate_budget",
        "description": (
            "Tính toán tổng ngân sách chuyến đi. "
            "Args JSON: {\"hotel_cost\": 800000, \"days\": 3, \"flight_cost\": 1500000, "
            "\"food_daily\": 300000, \"total_budget\": 5000000}"
        ),
    },
]
