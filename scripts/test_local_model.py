import time
import sys
import io
from pathlib import Path

from dotenv import load_dotenv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.core.provider_factory import create_provider


def main():
    load_dotenv(".env")

    print("[local-test] Loading Phi-3 local provider...", flush=True)
    started = time.time()
    provider = create_provider("local")
    print(
        f"[local-test] Loaded {provider.model_name} in {time.time() - started:.2f}s",
        flush=True,
    )

    prompt = "Tra loi dung format: Thought: ... Final Answer: Xin chao"
    print("[local-test] Generating short response...", flush=True)
    started = time.time()
    result = provider.generate(prompt)
    print(f"[local-test] Generated in {time.time() - started:.2f}s", flush=True)
    print("[local-test] Content:")
    print(result.get("content", ""))
    print("[local-test] Usage:", result.get("usage", {}))


if __name__ == "__main__":
    main()
