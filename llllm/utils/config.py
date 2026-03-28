"""Configuration helpers."""

from __future__ import annotations

import os

from llllm.exceptions import ProviderConfigurationError


ENV_VAR_BY_PROVIDER = {
    "openai": "OPENAI_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
}

FALLBACK_MODEL_ENV_VAR = "LLLLM_FALLBACK_MODEL"


def parse_model_spec(model_spec: str) -> tuple[str, str]:
    """Split 'provider:model' into its parts and validate the provider."""

    if ":" not in model_spec:
        raise ProviderConfigurationError(
            "Model must be in the format 'provider:model_name'."
        )

    provider, model = model_spec.split(":", 1)
    provider = provider.strip().lower()
    model = model.strip()

    if provider not in {"openai", "claude", "gemini", "ollama"}:
        raise ProviderConfigurationError(f"Unsupported provider '{provider}'.")
    if not model:
        raise ProviderConfigurationError("Model name cannot be empty.")

    return provider, model


def resolve_api_key(provider: str, explicit_api_key: str | None) -> str | None:
    """Prefer an explicit API key and fall back to environment variables."""

    if explicit_api_key:
        return explicit_api_key

    env_var = ENV_VAR_BY_PROVIDER.get(provider)
    if not env_var:
        return None

    return os.getenv(env_var)


def resolve_fallback_model() -> str | None:
    """Return the configured fallback provider:model target, if any."""

    value = os.getenv(FALLBACK_MODEL_ENV_VAR)
    if value is None:
        return None

    fallback_model = value.strip()
    return fallback_model or None
