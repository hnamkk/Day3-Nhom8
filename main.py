"""
main.py - Entry point cho Travel Planner ReAct Agent
Chay: python main.py
"""
import sys, io
# Force UTF-8 output so emoji displays correctly on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import os
import time
from dotenv import load_dotenv


# ── Load .env TRƯỚC khi import bất kỳ thứ gì khác ──────────────────────────
load_dotenv()

# ── Import providers ─────────────────────────────────────────────────────────
from src.core.provider_factory import create_provider

DEFAULT_PROVIDER = os.getenv("DEFAULT_PROVIDER", "google").lower()
try:
    llm = create_provider(DEFAULT_PROVIDER)
except Exception as exc:
    print(f"[ERROR] Không khởi tạo được provider '{DEFAULT_PROVIDER}': {exc}")
    sys.exit(1)

# ── Import Agent ─────────────────────────────────────────────────────────────
from src.agent.agent import ReActAgent
from src.agent.agent_v2 import ReActAgentV2
from src.tools.registry import TRAVEL_TOOLS

# ── Khai báo danh sách Tools cho Agent ──────────────────────────────────────
TOOLS = TRAVEL_TOOLS

AGENT_VERSION = os.getenv("AGENT_VERSION", "v1").lower()
if AGENT_VERSION == "v2":
    agent = ReActAgentV2(llm=llm, tools=TOOLS, max_steps=8)
else:
    agent = ReActAgent(llm=llm, tools=TOOLS, max_steps=8)

# ── Demo queries (sinh log cho TV4) ─────────────────────────────────────────
DEMO_QUERIES = [
    "Lên lịch trình du lịch Đà Nẵng 3 ngày với ngân sách 5 triệu đồng, phong cách nghỉ dưỡng.",
    "Tôi muốn đi Hội An 2 ngày theo phong cách ẩm thực, ngân sách 3 triệu. Hãy gợi ý khách sạn và tính ngân sách.",
    "Thời tiết Hà Nội tuần tới thế nào? Có nên đi du lịch không?",
]

# ── Interactive mode ─────────────────────────────────────────────────────────

def run_interactive():
    """Chay che do chat tuong tac."""
    print("\n" + "=" * 60)
    print("  Travel Planner ReAct Agent")
    print("  Provider:", DEFAULT_PROVIDER.upper(), "-", llm.model_name)
    print("  Agent:", AGENT_VERSION.upper())
    print("  Go 'exit' hoac 'quit' de thoat")
    print("=" * 60 + "\n")

    while True:
        try:
            user_input = input("Ban: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n[Agent] Tam biet!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "thoat", "q"):
            print("[Agent] Tam biet! Hen gap lai.")
            break

        print("\n[Agent dang suy nghi...]\n")
        answer = agent.run(user_input)
        print(f"Agent: {answer}\n")
        print("-" * 60)


def run_demo():
    """Chay cac cau hoi mau de sinh log cho TV4."""
    print("\n" + "=" * 60)
    print("  [DEMO MODE] Sinh log cho Thanh vien 4")
    print("  (Co delay 60s giua moi query de tranh rate limit)")
    print("=" * 60)

    for i, query in enumerate(DEMO_QUERIES, 1):
        print(f"\n[Demo {i}/{len(DEMO_QUERIES)}] {query}")
        print("-" * 60)
        answer = agent.run(query)
        print(f"Answer: {answer}")
        print("=" * 60)

        # Cho phep free-tier Gemini hoi phuc (5 req/phut)
        if i < len(DEMO_QUERIES):
            wait = 65
            print(f"\n[Rate limit] Doi {wait}s truoc khi chay demo tiep theo...")
            time.sleep(wait)

    print("\n[OK] Demo hoan tat. File log da duoc ghi vao thu muc logs/")



# ── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "interactive"

    if mode == "demo":
        run_demo()
    else:
        run_interactive()
