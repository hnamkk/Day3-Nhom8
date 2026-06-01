import time
from typing import Dict, Any, List
import statistics
from src.telemetry.logger import logger


class PerformanceTracker:
    """
    Tracking industry-standard metrics for LLMs.
    Collects per-request data and exposes convenience summaries.
    """
    def __init__(self):
        self.session_metrics: List[Dict[str, Any]] = []
        self.error_count = 0

    def track_request(self, provider: str, model: str, usage: Dict[str, int], latency_ms: int):
        """
        Logs a single request metric to our telemetry.
        `usage` should be a dict with keys: prompt_tokens, completion_tokens, total_tokens
        """
        prompt = usage.get("prompt_tokens", 0)
        completion = usage.get("completion_tokens", 0)
        total = usage.get("total_tokens", prompt + completion)

        metric = {
            "provider": provider,
            "model": model,
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": total,
            "latency_ms": latency_ms,
            "cost_estimate": self._calculate_cost(provider, model, prompt, completion)
        }
        self.session_metrics.append(metric)
        logger.log_event("LLM_METRIC", metric)

    def track_error(self, error_type: str, details: Dict[str, Any] = None):
        """Record a non-LLM error (parsing/tool/other) for the session."""
        self.error_count += 1
        payload = {"error_type": error_type, "details": details or {}}
        logger.log_event("SESSION_ERROR", payload)

    def _calculate_cost(self, provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Calculate estimated cost in USD using known pricing for popular models.

        - Gemini Flash (example): input 0.075$/1M tokens, output 0.30$/1M tokens
        - Fallback: use a conservative estimate of 0.10$/1M tokens for both directions
        """
        name = (model or "").lower()
        prov = (provider or "").lower()

        # Default rates (per 1M tokens)
        input_rate = 0.10
        output_rate = 0.10

        # Specific pricing for Gemini Flash
        if "gemini" in prov or "gemini" in name:
            # If provider/model indicates Gemini Flash, use the provided Flash rates
            # The lab spec: 0.075$/1M input, 0.30$/1M output
            input_rate = 0.075
            output_rate = 0.30

        cost = (prompt_tokens / 1_000_000) * input_rate + (completion_tokens / 1_000_000) * output_rate
        return float(cost)

    def get_summary(self) -> Dict[str, Any]:
        """Return summary statistics for the current session metrics."""
        total_requests = len(self.session_metrics) + self.error_count
        latencies = [m.get("latency_ms", 0) for m in self.session_metrics]
        costs = [m.get("cost_estimate", 0.0) for m in self.session_metrics]

        summary = {
            "total_requests": total_requests,
            "successful_requests": len(self.session_metrics),
            "error_count": self.error_count,
            "avg_latency_ms": statistics.mean(latencies) if latencies else 0,
            "median_latency_ms": statistics.median(latencies) if latencies else 0,
            "total_cost_usd": sum(costs),
            "avg_cost_per_request_usd": (sum(costs) / len(costs)) if costs else 0,
        }
        return summary

    @staticmethod
    def compare(chatbot_summary: Dict[str, Any], agent_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Compare two summaries (e.g., Chatbot vs Agent) and return a diff dict."""
        def _get(k, s):
            return s.get(k, 0)

        diff = {
            "latency_diff_ms": _get("avg_latency_ms", agent_summary) - _get("avg_latency_ms", chatbot_summary),
            "cost_diff_usd": _get("total_cost_usd", agent_summary) - _get("total_cost_usd", chatbot_summary),
            "success_rate_chatbot": (_get("successful_requests", chatbot_summary) / _get("total_requests", chatbot_summary)) if _get("total_requests", chatbot_summary) else 0,
            "success_rate_agent": (_get("successful_requests", agent_summary) / _get("total_requests", agent_summary)) if _get("total_requests", agent_summary) else 0,
        }
        return diff


# Global tracker instance
tracker = PerformanceTracker()
