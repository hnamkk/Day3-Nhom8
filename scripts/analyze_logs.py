import os
import json
from collections import defaultdict


def _parse_json_from_line(line: str):
    # Attempt to find the first JSON object in the line
    idx = line.find("{")
    if idx == -1:
        return None
    try:
        return json.loads(line[idx:])
    except Exception:
        try:
            # As a fallback, try to strip trailing chars
            j = line[idx:]
            j = j.rstrip('\n')
            return json.loads(j)
        except Exception:
            return None


def analyze_logs(log_dir: str = "logs"):
    stats = defaultdict(int)
    provider_latencies = defaultdict(list)
    agent_steps = []

    if not os.path.exists(log_dir):
        print(f"No log directory found at '{log_dir}'.")
        return

    for fname in os.listdir(log_dir):
        path = os.path.join(log_dir, fname)
        if not os.path.isfile(path):
            continue
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                obj = _parse_json_from_line(line)
                if not obj:
                    continue
                event = obj.get("event")
                data = obj.get("data", {})

                if event == "PARSING_ERROR":
                    stats["parsing_errors"] += 1
                if event == "HALLUCINATION_ERROR":
                    stats["hallucination_errors"] += 1
                if event in ("AGENT_END", "AGENT_V2_END"):
                    steps = data.get("steps")
                    if isinstance(steps, int):
                        agent_steps.append(steps)
                if event == "GUARDRAIL_TRIGGERED":
                    stats["guardrail_triggers"] += 1
                if event == "AGENT_V2_RETRY":
                    stats["agent_v2_retries"] += 1
                if event == "LLM_METRIC":
                    prov = data.get("provider", "unknown")
                    lat = data.get("latency_ms")
                    if isinstance(lat, (int, float)):
                        provider_latencies[prov].append(lat)

    print("==== Log Analysis Summary ====")
    print(f"Parsing errors: {stats.get('parsing_errors', 0)}")
    print(f"Hallucination errors: {stats.get('hallucination_errors', 0)}")
    print(f"Agent v2 retries: {stats.get('agent_v2_retries', 0)}")
    print(f"Guardrail triggers: {stats.get('guardrail_triggers', 0)}")

    if agent_steps:
        avg_steps = sum(agent_steps) / len(agent_steps)
        print(f"Agent runs: {len(agent_steps)}, avg loop steps: {avg_steps:.2f}")
    else:
        print("No AGENT_END entries found to compute loop counts.")

    print("\nLatency by provider (ms):")
    for p, vals in provider_latencies.items():
        if vals:
            print(f" - {p}: count={len(vals)}, avg={sum(vals)/len(vals):.1f} ms, median={sorted(vals)[len(vals)//2]:.1f} ms")

    print("==== End Summary ====")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Analyze logs produced by the lab tooling")
    parser.add_argument("--log-dir", default="logs", help="Directory containing log files")
    args = parser.parse_args()

    analyze_logs(args.log_dir)
