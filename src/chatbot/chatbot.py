import os
from typing import Optional

from src.core.llm_provider import LLMProvider

try:
    from src.core.openai_provider import OpenAIProvider
except Exception:
    OpenAIProvider = None

try:
    from src.core.gemini_provider import GeminiProvider
except Exception:
    GeminiProvider = None

try:
    from src.core.local_provider import LocalProvider
except Exception:
    LocalProvider = None


class Chatbot:
    """Simple baseline chatbot: calls LLM once and returns the reply.

    This implementation intentionally makes a single non-streaming call
    to the chosen LLM provider and does not call any tools.
    """

    def __init__(self, provider_name: Optional[str] = None, **kwargs):
        provider_name = provider_name or os.getenv("LLM_PROVIDER", "openai")
        provider_name = provider_name.lower()

        if provider_name == "openai" and OpenAIProvider is not None:
            api_key = kwargs.get("api_key") or os.getenv("OPENAI_API_KEY")
            self.provider: LLMProvider = OpenAIProvider(api_key=api_key)
        elif provider_name == "gemini" and GeminiProvider is not None:
            api_key = kwargs.get("api_key") or os.getenv("GEMINI_API_KEY")
            self.provider: LLMProvider = GeminiProvider(api_key=api_key)
        elif provider_name == "local" and LocalProvider is not None:
            model_path = kwargs.get("model_path") or os.getenv("LOCAL_MODEL_PATH")
            if not model_path:
                raise ValueError("LOCAL_MODEL_PATH must be set for local provider")
            self.provider: LLMProvider = LocalProvider(model_path)
        else:
            # Best-effort fallback: try available providers in order
            if OpenAIProvider is not None:
                api_key = kwargs.get("api_key") or os.getenv("OPENAI_API_KEY")
                self.provider = OpenAIProvider(api_key=api_key)
            elif GeminiProvider is not None:
                api_key = kwargs.get("api_key") or os.getenv("GEMINI_API_KEY")
                self.provider = GeminiProvider(api_key=api_key)
            elif LocalProvider is not None:
                model_path = kwargs.get("model_path") or os.getenv("LOCAL_MODEL_PATH")
                if not model_path:
                    raise ValueError("LOCAL_MODEL_PATH must be set for local provider")
                self.provider = LocalProvider(model_path)
            else:
                raise RuntimeError("No LLM provider available. Install a provider or set env vars.")

    def ask(self, user_input: str, system_prompt: Optional[str] = None) -> str:
        """Send single prompt to LLM and return the content string.

        Returns the raw assistant text. The baseline intentionally does no post-processing.
        """
        result = self.provider.generate(user_input, system_prompt=system_prompt)
        return result.get("content", "")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Chatbot baseline: single LLM call")
    parser.add_argument("prompt", nargs="+", help="User prompt text")
    parser.add_argument("--provider", choices=["openai", "gemini", "local"], help="LLM provider")
    parser.add_argument("--model-path", help="Path to local model (for local provider)")
    args = parser.parse_args()

    prompt = " ".join(args.prompt)
    kwargs = {}
    if args.model_path:
        kwargs["model_path"] = args.model_path

    bot = Chatbot(provider_name=args.provider, **kwargs)
    reply = bot.ask(prompt)
    print(reply)


if __name__ == "__main__":
    main()
