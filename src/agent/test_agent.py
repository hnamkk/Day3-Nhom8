import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.openai_provider import OpenAIProvider
from src.core.gemini_provider import GeminiProvider
from src.agent.agent import ReActAgent

def main():
    load_dotenv()
    
    provider_name = os.getenv("DEFAULT_PROVIDER", "openai").lower()
    if provider_name == "openai":
        provider = OpenAIProvider(model_name=os.getenv("DEFAULT_MODEL", "gpt-4o"), api_key=os.getenv("OPENAI_API_KEY"))
    else:
        provider = GeminiProvider(model_name=os.getenv("DEFAULT_MODEL", "gemini-2.5-flash"), api_key=os.getenv("GEMINI_API_KEY"))

    tools = [
        {
            "name": "search_destinations",
            "description": "Tra cứu địa điểm du lịch theo thành phố và phong cách (ví dụ: 'nghỉ dưỡng', 'ẩm thực', 'khám phá'). Input JSON: {\"city\": \"Hà Nội\", \"travel_style\": \"nghỉ dưỡng\"}"
        },
        {
            "name": "get_weather_forecast",
            "description": "Lấy dự báo thời tiết 3 ngày tới cho thành phố. Input JSON: {\"city\": \"Hà Nội\"}"
        },
        {
            "name": "check_hotel_prices",
            "description": "Tìm khách sạn phù hợp ngân sách mỗi đêm (VND). Input JSON: {\"city\": \"Hà Nội\", \"budget_per_night\": 1000000}"
        },
        {
            "name": "calculate_budget",
            "description": "Tính toán tổng ngân sách. Input JSON: {\"hotel_cost\": 1000000, \"days\": 3, \"flight_cost\": 2000000, \"food_daily\": 500000}"
        }
    ]

    agent = ReActAgent(llm=provider, tools=tools, max_steps=5)
    
    print("--- REACT AGENT V1 ---")
    question = input("User: ")
    
    print(f"\nProcessing...\n")
    answer = agent.run(question)
    
    print(f"\n=== FINAL ANSWER ===")
    print(answer)

if __name__ == "__main__":
    main()
