import time
import os
from typing import Dict, Any, Optional, Generator
from llama_cpp import Llama
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger

class LocalProvider(LLMProvider):
    """
    LLM Provider for local models using llama-cpp-python.
    Optimized for CPU usage with GGUF models.
    """
    def __init__(self, model_path: str, n_ctx: int = 4096, n_threads: Optional[int] = None):
        """
        Initialize the local Llama model.
        Args:
            model_path: Path to the .gguf model file.
            n_ctx: Context window size.
            n_threads: Number of CPU threads to use. Defaults to all available.
        """
        super().__init__(model_name=os.path.basename(model_path))
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found at {model_path}. Please download it first.")

        logger.log_event(
            "LOCAL_MODEL_LOAD_START",
            {"model_path": model_path, "n_ctx": n_ctx, "n_threads": n_threads},
        )
        start_time = time.time()

        # n_threads=None will use all available cores
        self.llm = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            n_threads=n_threads,
            verbose=False
        )
        logger.log_event(
            "LOCAL_MODEL_LOAD_END",
            {"model": self.model_name, "latency_ms": int((time.time() - start_time) * 1000)},
        )

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        logger.log_event(
            "LOCAL_GENERATE_START",
            {
                "model": self.model_name,
                "prompt_chars": len(prompt or ""),
                "has_system_prompt": bool(system_prompt),
            },
        )
        start_time = time.time()
        
        # Phi-3 / Llama-3 style formatting if not handled by a template
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"<|system|>\n{system_prompt}<|end|>\n<|user|>\n{prompt}<|end|>\n<|assistant|>"
        else:
            full_prompt = f"<|user|>\n{prompt}<|end|>\n<|assistant|>"

        max_tokens = int(os.getenv("LOCAL_MAX_TOKENS", "512"))
        response = self.llm(
            full_prompt,
            max_tokens=max_tokens,
            stop=["<|end|>", "Observation:"],
            echo=False
        )

        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)

        content = response["choices"][0]["text"].strip()
        usage = {
            "prompt_tokens": response["usage"]["prompt_tokens"],
            "completion_tokens": response["usage"]["completion_tokens"],
            "total_tokens": response["usage"]["total_tokens"]
        }

        logger.log_event(
            "LOCAL_GENERATE_END",
            {"model": self.model_name, "latency_ms": latency_ms, "completion_tokens": usage["completion_tokens"]},
        )

        return {
            "content": content,
            "usage": usage,
            "latency_ms": latency_ms,
            "provider": "local"
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"<|system|>\n{system_prompt}<|end|>\n<|user|>\n{prompt}<|end|>\n<|assistant|>"
        else:
            full_prompt = f"<|user|>\n{prompt}<|end|>\n<|assistant|>"

        max_tokens = int(os.getenv("LOCAL_MAX_TOKENS", "512"))
        stream = self.llm(
            full_prompt,
            max_tokens=max_tokens,
            stop=["<|end|>", "Observation:"],
            stream=True
        )

        for chunk in stream:
            token = chunk["choices"][0]["text"]
            if token:
                yield token
