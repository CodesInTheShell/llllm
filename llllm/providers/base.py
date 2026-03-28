"""Shared provider behavior."""

from __future__ import annotations

from typing import Any

import requests

from llllm.exceptions import ProviderConfigurationError, ProviderRequestError
from llllm.utils.config import resolve_api_key
from llllm.utils.input import InputPayload
from llllm.utils.normalize import build_response


class BaseProvider:
    """Base HTTP provider with shared request handling."""

    provider_name = ""
    api_key_env_var: str | None = None
    default_base_url = ""

    def __init__(
        self,
        *,
        model: str,
        api_key: str | None,
        timeout: float,
        base_url: str | None,
        headers: dict[str, str] | None,
    ) -> None:
        self.model = model
        self.api_key = resolve_api_key(self.provider_name, api_key)
        self.timeout = timeout
        self.base_url = (base_url or self.default_base_url).rstrip("/")
        self.extra_headers = headers or {}

        if not self.base_url:
            raise ProviderConfigurationError(
                f"Missing base URL for provider '{self.provider_name}'."
            )

    def generate(
        self,
        prompt: InputPayload,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        system: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        payload = self.build_payload(
            prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            system=system,
            **kwargs,
        )
        raw_response = self._post(self.endpoint_path, payload)
        normalized = self.normalize_response(raw_response)
        return build_response(
            raw_response=raw_response,
            provider=self.provider_name,
            model=self.model,
            normalized=normalized,
        )

    @property
    def endpoint_path(self) -> str:
        raise NotImplementedError

    def build_payload(
        self,
        prompt: InputPayload,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        system: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def normalize_response(self, raw_response: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        headers.update(self.extra_headers)
        return headers

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            response = requests.post(
                url,
                headers=self.build_headers(),
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "unknown"
            body = exc.response.text if exc.response is not None else str(exc)
            raise ProviderRequestError(
                f"{self.provider_name} request failed with status {status}: {body}"
            ) from exc
        except requests.RequestException as exc:
            raise ProviderRequestError(
                f"{self.provider_name} request failed: {exc}"
            ) from exc

    def require_api_key(self) -> str:
        if self.api_key:
            return self.api_key

        raise ProviderConfigurationError(
            f"Missing API key for provider '{self.provider_name}'. "
            f"Pass api_key or set {self.api_key_env_var}."
        )
