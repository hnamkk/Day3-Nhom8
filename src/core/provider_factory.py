import os
from pathlib import Path
from typing import Optional

from src.core.llm_provider import LLMProvider


def _resolve_local_model_path(explicit_path: Optional[str] = None) -> str:
    candidates = [
        explicit_path,
        os.getenv("LOCAL_MODEL_PATH"),
        "./model/Phi-3-mini-4k-instruct-q4.gguf",
        "./models/Phi-3-mini-4k-instruct-q4.gguf",
    ]

    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        if path.exists():
            return str(path)

    fallback = explicit_path or os.getenv("LOCAL_MODEL_PATH") or "./model/Phi-3-mini-4k-instruct-q4.gguf"
    return fallback


def create_provider(
    provider_name: Optional[str] = None,
    model_name: Optional[str] = None,
    local_model_path: Optional[str] = None,
) -> LLMProvider:
    provider = (provider_name or os.getenv("DEFAULT_PROVIDER", "google")).lower()

    if provider in ("google", "gemini"):
        from src.core.gemini_provider import GeminiProvider

        return GeminiProvider(
            model_name=model_name or os.getenv("DEFAULT_MODEL", "gemini-1.5-flash"),
            api_key=os.getenv("GEMINI_API_KEY"),
        )

    if provider == "openai":
        from src.core.openai_provider import OpenAIProvider

        return OpenAIProvider(
            model_name=model_name or os.getenv("DEFAULT_MODEL", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_API_KEY"),
        )

    if provider == "local":
        from src.core.local_provider import LocalProvider

        return LocalProvider(model_path=_resolve_local_model_path(local_model_path))

    raise ValueError("Provider không được hỗ trợ. Hãy dùng google, gemini, openai hoặc local.")
