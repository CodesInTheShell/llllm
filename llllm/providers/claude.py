"""Anthropic Messages API provider."""

from __future__ import annotations

from typing import Any

from .base import BaseProvider
from llllm.utils.input import (
    InputPayload,
    coerce_to_message_list,
    normalize_content_blocks,
    split_system_messages,
)


class ClaudeProvider(BaseProvider):
    provider_name = "claude"
    api_key_env_var = "ANTHROPIC_API_KEY"
    default_base_url = "https://api.anthropic.com"
    anthropic_version = "2023-06-01"

    @property
    def endpoint_path(self) -> str:
        return "/v1/messages"

    def build_headers(self) -> dict[str, str]:
        headers = super().build_headers()
        headers["x-api-key"] = self.require_api_key()
        headers["anthropic-version"] = self.anthropic_version
        return headers

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
            "model": self.model,
            "messages": [
                {
                    "role": message["role"],
                    "content": _claude_content(message["content"]),
                }
                for message in user_messages
            ],
            "max_tokens": max_tokens if max_tokens is not None else 1024,
        }
        if system_value:
            payload["system"] = system_value
        if temperature is not None:
            payload["temperature"] = temperature
        payload.update(kwargs)
        return payload

    def normalize_response(self, raw_response: dict[str, Any]) -> dict[str, Any]:
        text_parts = []
        for item in raw_response.get("content", []):
            if item.get("type") == "text" and item.get("text"):
                text_parts.append(item["text"])

        usage = raw_response.get("usage", {})
        input_tokens = usage.get("input_tokens")
        output_tokens = usage.get("output_tokens")
        total_tokens = None
        if None not in (input_tokens, output_tokens):
            total_tokens = input_tokens + output_tokens

        stop_reason = raw_response.get("stop_reason")
        if stop_reason is None:
            stop_reason = raw_response.get("stop_sequence")

        return {
            "text": "".join(text_parts),
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
            },
            "finish_reason": stop_reason,
        }


def _claude_content(content: str | list[Any]) -> str | list[dict[str, Any]]:
    blocks = normalize_content_blocks(content)
    if len(blocks) == 1 and blocks[0]["type"] == "text":
        return blocks[0]["text"]

    result = []
    for block in blocks:
        if block["type"] == "text":
            result.append({"type": "text", "text": block["text"]})
            continue

        source = _claude_source(block)
        result.append(
            {
                "type": "image" if block["type"] == "image" else "document",
                "source": source,
            }
        )
    return result


def _claude_source(block: dict[str, Any]) -> dict[str, Any]:
    if block["data"]:
        return {
            "type": "base64",
            "media_type": block["mime_type"],
            "data": block["data"],
        }
    if block["url"]:
        return {"type": "url", "url": block["url"]}
    if block["file_id"]:
        return {"type": "file", "file_id": block["file_id"]}
    if block["file_uri"]:
        return {"type": "url", "url": block["file_uri"]}
    raise ValueError("Unsupported Claude content block.")
