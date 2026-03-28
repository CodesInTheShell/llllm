"""Core client interface for the llllm package."""

from __future__ import annotations

import logging
from typing import Any

from .exceptions import ProviderConfigurationError, ProviderFallbackError
from .providers.claude import ClaudeProvider
from .providers.gemini import GeminiProvider
from .providers.ollama import OllamaProvider
from .providers.openai import OpenAIProvider
from .utils.config import parse_model_spec, resolve_fallback_model
from .utils.input import InputPayload, ensure_input_payload


PROVIDER_MAP = {
    "openai": OpenAIProvider,
    "claude": ClaudeProvider,
    "gemini": GeminiProvider,
    "ollama": OllamaProvider,
}

logger = logging.getLogger(__name__)


class LLLLM:
    """Unified sync client for multiple cloud and local LLM providers."""

    max_attempts = 5

    def __init__(
        self,
        model: str,
        *,
        api_key: str | None = None,
        timeout: float = 60.0,
        base_url: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.model_spec = model
        self.api_key = api_key
        self.timeout = timeout
        self.base_url = base_url
        self.headers = headers
        self.provider = self._build_provider(model, api_key, timeout, base_url, headers)

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

        normalized_prompt = ensure_input_payload(prompt)
        generation_kwargs = {
            "temperature": temperature,
            "max_tokens": max_tokens,
            "system": system,
            **kwargs,
        }

        try:
            return self._generate_with_retries(
                provider=self.provider,
                target=self.model_spec,
                prompt=normalized_prompt,
                **generation_kwargs,
            )
        except Exception as primary_exc:
            fallback_spec = resolve_fallback_model()
            if not fallback_spec:
                raise ProviderConfigurationError(
                    "Primary provider failed after 5 attempts and no fallback provider "
                    "is configured. Set LLLLM_FALLBACK_MODEL to 'provider:model'."
                ) from primary_exc

            if fallback_spec == self.model_spec:
                raise ProviderConfigurationError(
                    "LLLLM_FALLBACK_MODEL must be different from the primary model."
                ) from primary_exc

            logger.warning(
                "Primary provider %s failed after %s attempts. "
                "Switching to fallback provider %s.",
                self.model_spec,
                self.max_attempts,
                fallback_spec,
            )
            fallback_provider = self._build_provider(
                fallback_spec,
                None,
                self.timeout,
                None,
                self.headers,
            )

            try:
                return self._generate_with_retries(
                    provider=fallback_provider,
                    target=fallback_spec,
                    prompt=normalized_prompt,
                    **generation_kwargs,
                )
            except Exception as fallback_exc:
                raise ProviderFallbackError(
                    f"Primary provider '{self.model_spec}' failed after {self.max_attempts} "
                    f"attempts and fallback provider '{fallback_spec}' also failed after "
                    f"{self.max_attempts} attempts."
                ) from fallback_exc

    def _build_provider(
        self,
        model_spec: str,
        api_key: str | None,
        timeout: float,
        base_url: str | None,
        headers: dict[str, str] | None,
    ):
        provider_name, model_name = parse_model_spec(model_spec)
        provider_cls = PROVIDER_MAP[provider_name]
        return provider_cls(
            model=model_name,
            api_key=api_key,
            timeout=timeout,
            base_url=base_url,
            headers=headers,
        )

    def _generate_with_retries(
        self,
        *,
        provider: Any,
        target: str,
        prompt: InputPayload,
        **kwargs: Any,
    ) -> dict[str, Any]:
        last_exc: Exception | None = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                return provider.generate(prompt, **kwargs)
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                logger.warning(
                    "Attempt %s/%s failed for %s: %s",
                    attempt,
                    self.max_attempts,
                    target,
                    exc,
                )

        if last_exc is not None:
            raise last_exc

        raise RuntimeError(f"Retry loop for {target} exited without returning or raising.")
