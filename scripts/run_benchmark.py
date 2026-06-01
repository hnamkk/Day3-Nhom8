import time
from typing import Dict
from src.chatbot.chatbot import Chatbot
from src.agent.agent import ReActAgent
from src.agent.agent_v2 import ReActAgentV2
from src.telemetry.metrics import PerformanceTracker
from src.telemetry.logger import logger
from src.tools.registry import TRAVEL_TOOLS


def _estimate_tokens(text: str) -> int:
    # Very rough heuristic: 4 chars ~= 1 token
    return max(1, int(len(text) / 4))


class LLMWrapper:
    """Wrap an existing provider to capture usage/latency into a tracker."""
    def __init__(self, provider, tracker: PerformanceTracker):
        self._provider = provider
        self._tracker = tracker

    @property
    def model_name(self):
        return getattr(self._provider, "model_name", "unknown")

    def generate(self, prompt: str, system_prompt: str = None) -> Dict:
        start = time.time()
        res = self._provider.generate(prompt, system_prompt=system_prompt)
        # Some providers return latency and usage; provide fallbacks
        latency_ms = res.get("latency_ms") if isinstance(res.get("latency_ms"), (int, float)) else int((time.time() - start) * 1000)
        usage = res.get("usage") if isinstance(res.get("usage"), dict) else {
            "prompt_tokens": _estimate_tokens(prompt),
            "completion_tokens": _estimate_tokens(res.get("content", "")),
            "total_tokens": _estimate_tokens(prompt) + _estimate_tokens(res.get("content", "")),
        }
        # Track via the local tracker
        provider_name = getattr(self._provider, "__class__", type(self._provider)).__name__
        self._tracker.track_request(provider_name, getattr(self._provider, "model_name", "unknown"), usage, int(latency_ms))
        return res


def run_benchmark(prompts):
    # Instantiate baseline chatbot
    try:
        bot = Chatbot()
    except Exception as e:
        print("Failed to create Chatbot (no provider configured):", e)
        return

    # Local trackers for separation
    tracker_chat = PerformanceTracker()
    tracker_agent_v1 = PerformanceTracker()
    tracker_agent_v2 = PerformanceTracker()

    # Run Chatbot benchmark
    print("Running Chatbot baseline...")
    for p in prompts:
        start = time.time()
        # call provider.generate directly to capture usage
        res = bot.provider.generate(p)
        elapsed = int((time.time() - start) * 1000)

        usage = res.get("usage") if isinstance(res.get("usage"), dict) else {
            "prompt_tokens": _estimate_tokens(p),
            "completion_tokens": _estimate_tokens(res.get("content", "")),
            "total_tokens": _estimate_tokens(p) + _estimate_tokens(res.get("content", "")),
        }

        provider_name = getattr(bot.provider, "__class__", type(bot.provider)).__name__
        tracker_chat.track_request(provider_name, getattr(bot.provider, "model_name", "unknown"), usage, elapsed)
        logger.log_event("BENCHMARK_CHATBOT", {"prompt": p, "elapsed_ms": elapsed})

    tools = TRAVEL_TOOLS

    print("Running ReAct Agent v1 benchmark...")
    wrapped_llm_v1 = LLMWrapper(bot.provider, tracker_agent_v1)
    agent_v1 = ReActAgent(llm=wrapped_llm_v1, tools=tools, max_steps=5)
    for p in prompts:
        start = time.time()
        _ = agent_v1.run(p)
        elapsed = int((time.time() - start) * 1000)
        logger.log_event("BENCHMARK_AGENT_V1", {"prompt": p, "elapsed_ms": elapsed})

    print("Running ReAct Agent v2 benchmark...")
    wrapped_llm_v2 = LLMWrapper(bot.provider, tracker_agent_v2)
    agent_v2 = ReActAgentV2(llm=wrapped_llm_v2, tools=tools, max_steps=5)
    for p in prompts:
        start = time.time()
        _ = agent_v2.run(p)
        elapsed = int((time.time() - start) * 1000)
        logger.log_event("BENCHMARK_AGENT_V2", {"prompt": p, "elapsed_ms": elapsed})

    # Summaries
    chat_summary = tracker_chat.get_summary()
    agent_v1_summary = tracker_agent_v1.get_summary()
    agent_v2_summary = tracker_agent_v2.get_summary()

    print("\n--- Benchmark Results ---")
    print("Chatbot summary:", chat_summary)
    print("Agent v1 summary:", agent_v1_summary)
    print("Agent v2 summary:", agent_v2_summary)
    print("Chatbot vs Agent v1:", PerformanceTracker.compare(chat_summary, agent_v1_summary))
    print("Chatbot vs Agent v2:", PerformanceTracker.compare(chat_summary, agent_v2_summary))


if __name__ == '__main__':
    sample_prompts = [
        "Lên lịch 3 ngày ở Đà Nẵng với ngân sách 5 triệu",
        "Gợi ý khách sạn ở Hội An phù hợp cho gia đình",
        "Tư vấn lịch trình khám phá Hà Nội 2 ngày",
        "Tính ngân sách cho chuyến đi Đà Nẵng 4 ngày (bao gồm vé máy bay)",
        "Dự báo thời tiết Đà Nẵng cho cuối tuần này"
    ]

    run_benchmark(sample_prompts)
