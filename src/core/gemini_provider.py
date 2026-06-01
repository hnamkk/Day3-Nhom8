import os
import time
from google import genai
from typing import Dict, Any, Optional, Generator
from src.core.llm_provider import LLMProvider

class GeminiProvider(LLMProvider):
    def __init__(self, model_name: str = "gemini-1.5-flash", api_key: Optional[str] = None):
        super().__init__(model_name, api_key)
        self.client = genai.Client(api_key=self.api_key)
        self.max_retries = int(os.getenv("GEMINI_MAX_RETRIES", "2"))
        fallback_models = os.getenv("GEMINI_FALLBACK_MODELS", "")
        self.fallback_models = [
            model.strip()
            for model in fallback_models.split(",")
            if model.strip() and model.strip() != self.model_name
        ]

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()
        
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"System: {system_prompt}\n\nUser: {prompt}"

        response = self._generate_with_retry(full_prompt)

        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)

        usage_metadata = getattr(response, "usage_metadata", None)
        prompt_tokens = getattr(usage_metadata, "prompt_token_count", 0) if usage_metadata else 0
        completion_tokens = getattr(usage_metadata, "candidates_token_count", 0) if usage_metadata else 0
        total_tokens = getattr(usage_metadata, "total_token_count", prompt_tokens + completion_tokens) if usage_metadata else prompt_tokens + completion_tokens

        usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens
        }

        return {
            "content": response.text or "",
            "usage": usage,
            "latency_ms": latency_ms,
            "provider": "google"
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"System: {system_prompt}\n\nUser: {prompt}"

        stream = self.client.models.generate_content_stream(
            model=self.model_name,
            contents=full_prompt,
        )
        for chunk in stream:
            if chunk.text:
                yield chunk.text

    def _generate_with_retry(self, full_prompt: str):
        models_to_try = [self.model_name] + self.fallback_models
        last_error = None

        for model in models_to_try:
            for attempt in range(self.max_retries + 1):
                try:
                    response = self.client.models.generate_content(
                        model=model,
                        contents=full_prompt,
                    )
                    if model != self.model_name:
                        self.model_name = model
                    return response
                except Exception as exc:
                    last_error = exc
                    if not self._is_retryable_error(exc) or attempt >= self.max_retries:
                        break
                    time.sleep(min(2 ** attempt, 4))

        raise RuntimeError(self._format_gemini_error(last_error))

    def _is_retryable_error(self, exc: Exception) -> bool:
        message = str(exc).lower()
        return "503" in message or "unavailable" in message or "high demand" in message

    def _format_gemini_error(self, exc: Optional[Exception]) -> str:
        message = str(exc) if exc else "Unknown Gemini error"
        if self._is_retryable_error(Exception(message)):
            return (
                "Gemini API đang quá tải (503 UNAVAILABLE). "
                "Bạn có thể thử lại sau, đổi DEFAULT_MODEL, cấu hình GEMINI_FALLBACK_MODELS, "
                "hoặc chuyển sang Phi-3 local để demo offline."
            )
        return message
