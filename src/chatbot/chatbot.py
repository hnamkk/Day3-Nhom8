import os
from typing import Optional

from src.core.llm_provider import LLMProvider
from src.core.provider_factory import create_provider


class Chatbot:
    """Simple baseline chatbot: calls LLM once and returns the reply.

    This implementation intentionally makes a single non-streaming call
    to the chosen LLM provider and does not call any tools.
    """

    def __init__(self, provider_name: Optional[str] = None, **kwargs):
        provider_name = provider_name or os.getenv("LLM_PROVIDER") or os.getenv("DEFAULT_PROVIDER", "openai")
        self.provider: LLMProvider = create_provider(
            provider_name=provider_name,
            model_name=kwargs.get("model_name"),
            local_model_path=kwargs.get("model_path"),
        )

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
