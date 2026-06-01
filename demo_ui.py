import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional

from dotenv import load_dotenv

from src.agent.agent import ReActAgent
from src.agent.agent_v2 import ReActAgentV2
from src.core.provider_factory import create_provider
from src.telemetry.logger import logger
from src.tools.registry import TRAVEL_TOOLS


load_dotenv()

PROVIDER_CACHE: Dict[str, Any] = {}
DEFAULT_DEMO_PROVIDER = os.getenv("DEMO_PROVIDER", "local").lower()
FORCED_DEMO_PROVIDER = os.getenv("DEMO_FORCE_PROVIDER", "").lower().strip()

BASELINE_SYSTEM_PROMPT = """
You are a baseline travel chatbot.
Answer in Vietnamese only. Keep the answer under 8 bullet points.
Do not call tools. Do not claim you checked real weather, hotels, or prices.
If the user asks for a budget, give only a rough estimate and say it is not verified.
"""


class TrackingProvider:
    def __init__(self, provider: Any):
        self.provider = provider
        self.model_name = getattr(provider, "model_name", "unknown")
        self.calls = 0
        self.total_latency_ms = 0
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        started = time.time()
        result = self.provider.generate(prompt, system_prompt=system_prompt)
        latency_ms = result.get("latency_ms")
        if not isinstance(latency_ms, (int, float)):
            latency_ms = int((time.time() - started) * 1000)

        usage = result.get("usage") or {}
        prompt_tokens = int(usage.get("prompt_tokens", max(1, len(prompt) // 4)))
        completion_tokens = int(usage.get("completion_tokens", max(1, len(result.get("content", "")) // 4)))

        self.calls += 1
        self.total_latency_ms += int(latency_ms)
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        return result

    def metrics(self) -> Dict[str, Any]:
        return {
            "llm_calls": self.calls,
            "latency_ms": self.total_latency_ms,
            "prompt_tokens": self.total_prompt_tokens,
            "completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_prompt_tokens + self.total_completion_tokens,
        }


def get_provider(provider_name: str):
    provider_name = (provider_name or "google").lower()
    cache_key = provider_name
    if cache_key not in PROVIDER_CACHE:
        logger.log_event("DEMO_PROVIDER_LOAD_START", {"provider": provider_name})
        PROVIDER_CACHE[cache_key] = create_provider(provider_name)
        logger.log_event(
            "DEMO_PROVIDER_LOAD_END",
            {
                "provider": provider_name,
                "model": getattr(PROVIDER_CACHE[cache_key], "model_name", "unknown"),
            },
        )
    return PROVIDER_CACHE[cache_key]


def run_baseline(prompt: str, provider_name: str) -> Dict[str, Any]:
    tracker = TrackingProvider(get_provider(provider_name))
    started = time.time()
    result = tracker.generate(prompt, system_prompt=BASELINE_SYSTEM_PROMPT)
    metrics = tracker.metrics()
    metrics["wall_time_ms"] = int((time.time() - started) * 1000)
    return {
        "answer": result.get("content", "").strip(),
        "metrics": metrics,
        "trace": [],
        "model": tracker.model_name,
    }


def run_agent(prompt: str, provider_name: str, agent_version: str) -> Dict[str, Any]:
    tracker = TrackingProvider(get_provider(provider_name))
    started = time.time()

    if agent_version == "v1":
        agent = ReActAgent(llm=tracker, tools=TRAVEL_TOOLS, max_steps=6)
        answer = agent.run(prompt)
        trace = []
        agent_metrics = {"steps": None, "tool_calls": None, "parse_retries": 0}
    else:
        agent = ReActAgentV2(llm=tracker, tools=TRAVEL_TOOLS, max_steps=6)
        result = agent.run_with_trace(prompt)
        answer = result["answer"]
        trace = result["trace"]
        agent_metrics = result["metrics"]

    metrics = tracker.metrics()
    metrics.update(agent_metrics)
    metrics["wall_time_ms"] = int((time.time() - started) * 1000)
    return {
        "answer": answer,
        "metrics": metrics,
        "trace": trace,
        "model": tracker.model_name,
    }


def make_json_response(handler: BaseHTTPRequestHandler, status: int, payload: Dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def friendly_error_message(exc: Exception) -> str:
    message = str(exc)
    lowered = message.lower()
    if "503" in lowered or "unavailable" in lowered or "high demand" in lowered:
        return (
            "Gemini API đang quá tải (503 UNAVAILABLE). "
            "Hãy thử lại sau, đổi model Gemini trong .env, hoặc chọn Phi-3 local để demo offline."
        )
    return message


def is_gemini_capacity_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "503" in message or "unavailable" in message or "high demand" in message


def run_request(kind: str, prompt: str, provider: str, agent_version: str) -> Dict[str, Any]:
    response: Dict[str, Any] = {}
    if kind in ("compare", "baseline"):
        response["baseline"] = run_baseline(prompt, provider)
    if kind in ("compare", "agent"):
        response["agent"] = run_agent(prompt, provider, agent_version)
    return response


HTML = r"""<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Travel Planner Demo</title>
  <style>
    :root {
      --bg: #f7f8fb;
      --ink: #172033;
      --muted: #627087;
      --line: #d9dee8;
      --panel: #ffffff;
      --brand: #116466;
      --brand-2: #c85f3e;
      --agent: #174ea6;
      --good: #257942;
      --warn: #9a5b00;
      --shadow: 0 10px 26px rgba(23, 32, 51, 0.08);
    }

    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.45;
    }

    header {
      background: #ffffff;
      border-bottom: 1px solid var(--line);
      padding: 18px 24px;
    }

    .topbar {
      max-width: 1240px;
      margin: 0 auto;
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: center;
    }

    h1 {
      margin: 0;
      font-size: 24px;
      letter-spacing: 0;
    }

    .subtitle {
      margin: 4px 0 0;
      color: var(--muted);
      font-size: 14px;
    }

    main {
      max-width: 1240px;
      margin: 0 auto;
      padding: 20px 24px 36px;
    }

    .controls {
      display: grid;
      grid-template-columns: 1fr 190px 170px;
      gap: 12px;
      align-items: end;
      margin-bottom: 16px;
    }

    label {
      display: block;
      color: var(--muted);
      font-size: 13px;
      font-weight: 650;
      margin-bottom: 6px;
    }

    textarea, select {
      width: 100%;
      border: 1px solid var(--line);
      background: #fff;
      color: var(--ink);
      border-radius: 8px;
      padding: 10px 12px;
      font: inherit;
      outline: none;
    }

    textarea {
      min-height: 84px;
      resize: vertical;
    }

    textarea:focus, select:focus {
      border-color: var(--brand);
      box-shadow: 0 0 0 3px rgba(17, 100, 102, 0.13);
    }

    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 18px;
    }

    button {
      border: 0;
      border-radius: 8px;
      background: var(--brand);
      color: white;
      font-weight: 700;
      padding: 10px 14px;
      cursor: pointer;
      min-height: 40px;
    }

    button.secondary { background: var(--agent); }
    button.ghost {
      background: #eef2f7;
      color: var(--ink);
    }
    button:disabled {
      opacity: .65;
      cursor: wait;
    }

    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
      align-items: start;
    }

    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      overflow: hidden;
    }

    .panel-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      padding: 12px 14px;
      border-bottom: 1px solid var(--line);
    }

    .panel-head h2 {
      margin: 0;
      font-size: 16px;
      letter-spacing: 0;
    }

    .badge {
      color: var(--muted);
      font-size: 12px;
      background: #f0f3f8;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 4px 8px;
      white-space: nowrap;
    }

    .answer {
      min-height: 260px;
      padding: 14px;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }

    .metrics {
      border-top: 1px solid var(--line);
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
    }

    .metric {
      padding: 10px 12px;
      border-right: 1px solid var(--line);
      min-height: 64px;
    }

    .metric:last-child { border-right: 0; }
    .metric .k {
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 3px;
    }
    .metric .v {
      font-size: 18px;
      font-weight: 750;
    }

    .trace {
      margin-top: 16px;
    }

    .trace-list {
      padding: 10px 14px 14px;
      display: grid;
      gap: 10px;
    }

    .trace-item {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfcfe;
      padding: 10px;
    }

    .trace-title {
      font-weight: 750;
      color: var(--agent);
      margin-bottom: 7px;
    }

    pre {
      margin: 0;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      font-family: "Cascadia Code", Consolas, monospace;
      font-size: 12px;
    }

    .status {
      min-height: 22px;
      color: var(--muted);
      font-size: 14px;
      margin-bottom: 10px;
    }

    .error {
      color: #a22;
      font-weight: 700;
    }

    @media (max-width: 880px) {
      .controls, .grid {
        grid-template-columns: 1fr;
      }
      .metrics {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
    }
  </style>
</head>
<body>
  <header>
    <div class="topbar">
      <div>
        <h1>Travel Planner Demo</h1>
        <p class="subtitle">So sánh Chatbot Baseline với ReAct Agent và trace Thought/Action/Observation.</p>
      </div>
      <span class="badge">Gemini hoặc Phi-3 local</span>
    </div>
  </header>

  <main>
    <section class="controls">
      <div>
        <label for="prompt">Prompt demo</label>
        <textarea id="prompt">Lên lịch Đà Nẵng 3 ngày, ngân sách 5 triệu, thích nghỉ dưỡng. Hãy gợi ý khách sạn và tính ngân sách.</textarea>
      </div>
      <div>
        <label for="provider">Model provider</label>
        <select id="provider">
          <option value="local" selected>Phi-3 local</option>
          <option value="google">Gemini</option>
          <option value="openai">OpenAI</option>
        </select>
      </div>
      <div>
        <label for="agentVersion">Agent</label>
        <select id="agentVersion">
          <option value="v2">Agent V2</option>
          <option value="v1">Agent V1</option>
        </select>
      </div>
    </section>

    <div class="actions">
      <button id="runCompare">Run Compare</button>
      <button class="ghost" id="runBaseline">Run Baseline</button>
      <button class="secondary" id="runAgent">Run Agent</button>
      <button class="ghost" id="clear">Clear</button>
    </div>

    <div id="status" class="status"></div>

    <section class="grid">
      <article class="panel">
        <div class="panel-head">
          <h2>Chatbot Baseline</h2>
          <span id="baselineModel" class="badge">No run</span>
        </div>
        <div id="baselineAnswer" class="answer">Baseline trả lời trực tiếp, không gọi tools.</div>
        <div class="metrics">
          <div class="metric"><div class="k">Latency</div><div id="baselineLatency" class="v">-</div></div>
          <div class="metric"><div class="k">LLM calls</div><div id="baselineCalls" class="v">-</div></div>
          <div class="metric"><div class="k">Tool calls</div><div class="v">0</div></div>
          <div class="metric"><div class="k">Tokens</div><div id="baselineTokens" class="v">-</div></div>
        </div>
      </article>

      <article class="panel">
        <div class="panel-head">
          <h2>ReAct Agent</h2>
          <span id="agentModel" class="badge">No run</span>
        </div>
        <div id="agentAnswer" class="answer">Agent sẽ gọi tools theo vòng Thought -> Action -> Observation.</div>
        <div class="metrics">
          <div class="metric"><div class="k">Latency</div><div id="agentLatency" class="v">-</div></div>
          <div class="metric"><div class="k">LLM calls</div><div id="agentCalls" class="v">-</div></div>
          <div class="metric"><div class="k">Tool calls</div><div id="agentTools" class="v">-</div></div>
          <div class="metric"><div class="k">Retries</div><div id="agentRetries" class="v">-</div></div>
        </div>
      </article>
    </section>

    <section class="panel trace">
      <div class="panel-head">
        <h2>Agent Trace</h2>
        <span class="badge">Agent V2 hiển thị đầy đủ trace</span>
      </div>
      <div id="traceList" class="trace-list">
        <div class="trace-item"><pre>Chưa có trace.</pre></div>
      </div>
    </section>
  </main>

  <script>
    const $ = (id) => document.getElementById(id);
    const status = $("status");

    function promptValue() {
      return $("prompt").value.trim();
    }

    function requestPayload(kind) {
      return {
        kind,
        prompt: promptValue(),
        provider: $("provider").value,
        agent_version: $("agentVersion").value
      };
    }

    async function callApi(kind) {
      const response = await fetch("/api/run", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(requestPayload(kind))
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Request failed");
      }
      return data;
    }

    function metricValue(value, suffix = "") {
      if (value === null || value === undefined) return "-";
      return `${value}${suffix}`;
    }

    function renderBaseline(data) {
      $("baselineAnswer").textContent = data.answer || "";
      $("baselineModel").textContent = data.model || "model";
      $("baselineLatency").textContent = metricValue(data.metrics?.wall_time_ms, "ms");
      $("baselineCalls").textContent = metricValue(data.metrics?.llm_calls);
      $("baselineTokens").textContent = metricValue(data.metrics?.total_tokens);
    }

    function renderAgent(data) {
      $("agentAnswer").textContent = data.answer || "";
      $("agentModel").textContent = data.model || "model";
      $("agentLatency").textContent = metricValue(data.metrics?.wall_time_ms, "ms");
      $("agentCalls").textContent = metricValue(data.metrics?.llm_calls);
      $("agentTools").textContent = metricValue(data.metrics?.tool_calls);
      $("agentRetries").textContent = metricValue(data.metrics?.parse_retries);
      renderTrace(data.trace || []);
    }

    function renderTrace(trace) {
      if (!trace.length) {
        $("traceList").innerHTML = `<div class="trace-item"><pre>Agent V1 chưa expose trace trong UI. Xem logs/ để phân tích chi tiết.</pre></div>`;
        return;
      }
      $("traceList").innerHTML = trace.map(item => {
        const parts = [];
        if (item.llm_response) parts.push(`LLM:\n${item.llm_response}`);
        if (item.action) parts.push(`Action:\n${item.action}`);
        if (item.action_input) parts.push(`Action Input:\n${item.action_input}`);
        if (item.observation) parts.push(`Observation:\n${item.observation}`);
        if (item.final_answer) parts.push(`Final Answer:\n${item.final_answer}`);
        if (item.error) parts.push(`Error:\n${item.error}`);
        return `<div class="trace-item">
          <div class="trace-title">Step ${item.step} - ${item.event}</div>
          <pre>${escapeHtml(parts.join("\n\n"))}</pre>
        </div>`;
      }).join("");
    }

    function escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;");
    }

    async function run(kind) {
      if (!promptValue()) {
        status.innerHTML = `<span class="error">Prompt không được để trống.</span>`;
        return;
      }
      setBusy(true);
      const provider = $("provider").value;
      if (provider === "local") {
        status.textContent = "Phi-3 local đang chạy trên CPU. Lần đầu có thể mất 30 giây đến vài phút...";
      } else {
        status.textContent = kind === "compare" ? "Đang chạy baseline và agent..." : "Đang chạy...";
      }
      try {
        const data = await callApi(kind);
        if (data.baseline) renderBaseline(data.baseline);
        if (data.agent) renderAgent(data.agent);
        if (data.fallback) {
          status.textContent = data.fallback.reason || "Đã fallback sang provider khác.";
        } else {
          status.textContent = "Hoàn tất.";
        }
      } catch (error) {
        const message = error.message === "Failed to fetch"
          ? "Không gọi được backend. Hãy kiểm tra terminal đang chạy python demo_ui.py còn sống không."
          : error.message;
        status.innerHTML = `<span class="error">${escapeHtml(message)}</span>`;
      } finally {
        setBusy(false);
      }
    }

    function setBusy(busy) {
      ["runCompare", "runBaseline", "runAgent", "clear"].forEach(id => $(id).disabled = busy);
    }

    $("runCompare").addEventListener("click", () => run("compare"));
    $("runBaseline").addEventListener("click", () => run("baseline"));
    $("runAgent").addEventListener("click", () => run("agent"));
    $("clear").addEventListener("click", () => {
      $("baselineAnswer").textContent = "Baseline trả lời trực tiếp, không gọi tools.";
      $("agentAnswer").textContent = "Agent sẽ gọi tools theo vòng Thought -> Action -> Observation.";
      $("traceList").innerHTML = `<div class="trace-item"><pre>Chưa có trace.</pre></div>`;
      ["baselineLatency", "baselineCalls", "baselineTokens", "agentLatency", "agentCalls", "agentTools", "agentRetries"].forEach(id => $(id).textContent = "-");
      $("baselineModel").textContent = "No run";
      $("agentModel").textContent = "No run";
      status.textContent = "";
    });
  </script>
</body>
</html>
"""


class DemoHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path not in ("/", "/index.html"):
            self.send_error(404)
            return
        body = HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path != "/api/run":
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            prompt = (payload.get("prompt") or "").strip()
            if not prompt:
                raise ValueError("Prompt không được để trống.")

            kind = payload.get("kind", "compare")
            requested_provider = payload.get("provider", DEFAULT_DEMO_PROVIDER)
            provider = FORCED_DEMO_PROVIDER or requested_provider or DEFAULT_DEMO_PROVIDER
            agent_version = payload.get("agent_version", "v2")

            logger.log_event(
                "DEMO_REQUEST_START",
                {
                    "kind": kind,
                    "requested_provider": requested_provider,
                    "provider": provider,
                    "agent_version": agent_version,
                    "prompt_chars": len(prompt),
                },
            )

            try:
                response = run_request(kind, prompt, provider, agent_version)
            except Exception as exc:
                if provider != "local" and is_gemini_capacity_error(exc):
                    logger.log_event(
                        "DEMO_PROVIDER_FALLBACK",
                        {
                            "from_provider": provider,
                            "to_provider": "local",
                            "reason": str(exc),
                        },
                    )
                    response = run_request(kind, prompt, "local", agent_version)
                    response["fallback"] = {
                        "from": provider,
                        "to": "local",
                        "reason": "Gemini API đang quá tải, đã tự chuyển sang Phi-3 local.",
                    }
                else:
                    raise

            logger.log_event("DEMO_REQUEST_END", {"kind": kind, "provider": provider})
            make_json_response(self, 200, response)
        except Exception as exc:
            error_message = friendly_error_message(exc)
            logger.log_event("DEMO_REQUEST_ERROR", {"error": str(exc), "friendly_error": error_message})
            make_json_response(self, 500, {"error": error_message})

    def log_message(self, format: str, *args: Any) -> None:
        sys.stdout.write("[demo-ui] " + format % args + "\n")


def main() -> None:
    host = os.getenv("DEMO_HOST", "127.0.0.1")
    port = int(os.getenv("DEMO_PORT", "7860"))
    server = ThreadingHTTPServer((host, port), DemoHandler)
    print(f"Travel Planner demo UI: http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    server.serve_forever()


if __name__ == "__main__":
    main()
