"""Google Gemini Generative Language API provider."""

from __future__ import annotations

from typing import Any

from .base import BaseProvider
from llllm.utils.input import (
    InputPayload,
    coerce_to_message_list,
    normalize_content_blocks,
    split_system_messages,
)


class GeminiProvider(BaseProvider):
    provider_name = "gemini"
    api_key_env_var = "GEMINI_API_KEY"
    default_base_url = "https://generativelanguage.googleapis.com"

    @property
    def endpoint_path(self) -> str:
        return f"/v1beta/models/{self.model}:generateContent"

    def build_headers(self) -> dict[str, str]:
        return super().build_headers()

    def build_payload(
        self,
        prompt: InputPayload,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        system: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        messages = coerce_to_message_list(prompt)
        system_value, user_messages = split_system_messages(messages, system)

        payload: dict[str, Any] = {
            "contents": [_gemini_message(message) for message in user_messages]
        }
        generation_config: dict[str, Any] = {}
        if temperature is not None:
            generation_config["temperature"] = temperature
        if max_tokens is not None:
            generation_config["maxOutputTokens"] = max_tokens
        if generation_config:
            payload["generationConfig"] = generation_config
        if system_value:
            payload["systemInstruction"] = {"parts": [{"text": system_value}]}
        payload.update(kwargs)
        return payload

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        api_key = self.require_api_key()
        return super()._post(f"{path}?key={api_key}", payload)

    def normalize_response(self, raw_response: dict[str, Any]) -> dict[str, Any]:
        text_parts: list[str] = []
        finish_reason = None

        for candidate in raw_response.get("candidates", []):
            finish_reason = finish_reason or candidate.get("finishReason")
            content = candidate.get("content", {})
            for part in content.get("parts", []):
                text = part.get("text")
                if text:
                    text_parts.append(text)

        usage = raw_response.get("usageMetadata", {})
        input_tokens = usage.get("promptTokenCount")
        output_tokens = usage.get("candidatesTokenCount")
        total_tokens = usage.get("totalTokenCount")
        if total_tokens is None and None not in (input_tokens, output_tokens):
            total_tokens = input_tokens + output_tokens

        return {
            "text": "".join(text_parts),
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
            },
            "finish_reason": finish_reason,
        }


def _gemini_message(message: dict[str, Any]) -> dict[str, Any]:
    role = message["role"]
    content = message["content"]
    parts = _gemini_parts(content)

    return {
        "role": "model" if role == "assistant" else role,
        "parts": parts,
    }


def _gemini_parts(content: str | list[Any]) -> list[dict[str, Any]]:
    result = []
    for block in normalize_content_blocks(content):
        if block["type"] == "text":
            result.append({"text": block["text"]})
            continue

        if block["file_uri"] or block["url"]:
            result.append(
                {
                    "file_data": {
                        "mime_type": block["mime_type"],
                        "file_uri": block["file_uri"] or block["url"],
                    }
                }
            )
            continue

        result.append(
            {
                "inline_data": {
                    "mime_type": block["mime_type"],
                    "data": block["data"],
                }
            }
        )
    return result
