"""Ollama local generate API provider."""

from __future__ import annotations

from typing import Any

from .base import BaseProvider
from llllm.exceptions import InvalidInputError
from llllm.utils.input import InputPayload, coerce_to_message_list, normalize_content_blocks


class OllamaProvider(BaseProvider):
    provider_name = "ollama"
    api_key_env_var = None
    default_base_url = "http://localhost:11434"

    @property
    def endpoint_path(self) -> str:
        return "/api/chat"

    def build_payload(
        self,
        prompt: InputPayload,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        system: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        options: dict[str, Any] = kwargs.pop("options", {}).copy()
        if temperature is not None:
            options["temperature"] = temperature
        if max_tokens is not None:
            options["num_predict"] = max_tokens

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": _ollama_messages(prompt, system),
            "stream": False,
        }
        if options:
            payload["options"] = options
        payload.update(kwargs)
        return payload

    def normalize_response(self, raw_response: dict[str, Any]) -> dict[str, Any]:
        prompt_tokens = raw_response.get("prompt_eval_count")
        output_tokens = raw_response.get("eval_count")
        total_tokens = None
        if None not in (prompt_tokens, output_tokens):
            total_tokens = prompt_tokens + output_tokens

        return {
            "text": raw_response.get("message", {}).get(
                "content",
                raw_response.get("response", ""),
            ),
            "usage": {
                "input_tokens": prompt_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
            },
            "finish_reason": raw_response.get("done_reason"),
        }


def _ollama_messages(
    prompt: InputPayload,
    system: str | None,
) -> list[dict[str, Any]]:
    messages = coerce_to_message_list(prompt)
    if system:
        messages = [{"role": "system", "content": system}] + messages

    return [_ollama_message(message) for message in messages]


def _ollama_message(message: dict[str, Any]) -> dict[str, Any]:
    text_parts: list[str] = []
    images: list[str] = []

    for block in normalize_content_blocks(message["content"]):
        if block["type"] == "text":
            text_parts.append(block["text"])
            continue

        mime_type = block["mime_type"] or ""
        if not mime_type.startswith("image/"):
            raise InvalidInputError(
                "Ollama currently supports image parts only, not non-image file parts."
            )
        if not block["data"]:
            raise InvalidInputError(
                "Ollama image parts require inline base64 data or a local file path."
            )
        images.append(block["data"])

    result = {
        "role": message["role"],
        "content": "\n".join(part for part in text_parts if part),
    }
    if images:
        result["images"] = images
    return result
