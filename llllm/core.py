"""Core client interface for the llllm package."""

from __future__ import annotations

from typing import Any

from .providers.claude import ClaudeProvider
from .providers.gemini import GeminiProvider
from .providers.ollama import OllamaProvider
from .providers.openai import OpenAIProvider
from .utils.config import parse_model_spec
from .utils.input import InputPayload, ensure_input_payload


PROVIDER_MAP = {
    "openai": OpenAIProvider,
    "claude": ClaudeProvider,
    "gemini": GeminiProvider,
    "ollama": OllamaProvider,
}


class LLLLM:
    """Unified sync client for multiple cloud and local LLM providers."""

    def __init__(
        self,
        model: str,
        *,
        api_key: str | None = None,
        timeout: float = 60.0,
        base_url: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        provider_name, model_name = parse_model_spec(model)
        provider_cls = PROVIDER_MAP[provider_name]
        self.provider = provider_cls(
            model=model_name,
            api_key=api_key,
            timeout=timeout,
            base_url=base_url,
            headers=headers,
        )

    def gen(
        self,
        prompt: InputPayload,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        system: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Generate a text response using the configured provider."""

        return self.provider.generate(
            ensure_input_payload(prompt),
            temperature=temperature,
            max_tokens=max_tokens,
            system=system,
            **kwargs,
        )
