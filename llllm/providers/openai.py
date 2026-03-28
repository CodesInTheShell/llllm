"""OpenAI Responses API provider."""

from __future__ import annotations

import os
from typing import Any

from .base import BaseProvider
from llllm.utils.input import (
    InputPayload,
    coerce_to_message_list,
    normalize_content_blocks,
)


class OpenAIProvider(BaseProvider):
    provider_name = "openai"
    api_key_env_var = "OPENAI_API_KEY"
    default_base_url = "https://api.openai.com"

    @property
    def endpoint_path(self) -> str:
        return "/v1/responses"

    def build_headers(self) -> dict[str, str]:
        headers = super().build_headers()
        headers["Authorization"] = f"Bearer {self.require_api_key()}"
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
        input_payload: str | list[dict[str, Any]]
        if isinstance(prompt, str):
            input_payload = prompt
        else:
            input_payload = [
                {
                    "role": message["role"],
                    "content": _openai_content(message["content"]),
                }
                for message in coerce_to_message_list(prompt)
            ]

        payload: dict[str, Any] = {
            "model": self.model,
            "input": input_payload,
        }
        if system:
            payload["instructions"] = system
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_output_tokens"] = max_tokens
        payload.update(kwargs)
        return payload

    def normalize_response(self, raw_response: dict[str, Any]) -> dict[str, Any]:
        text_parts: list[str] = []
        for output in raw_response.get("output", []):
            for item in output.get("content", []):
                text = item.get("text")
                if text:
                    text_parts.append(text)

        usage = raw_response.get("usage", {})
        input_tokens = usage.get("input_tokens")
        output_tokens = usage.get("output_tokens")
        total_tokens = usage.get("total_tokens")
        if total_tokens is None and None not in (input_tokens, output_tokens):
            total_tokens = input_tokens + output_tokens

        return {
            "text": "".join(text_parts),
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
            },
            "finish_reason": raw_response.get("status"),
        }


def _openai_content(content: str | list[Any]) -> list[dict[str, Any]]:
    blocks = normalize_content_blocks(content)
    result = []
    for block in blocks:
        if block["type"] == "text":
            result.append({"type": "input_text", "text": block["text"]})
            continue

        if block["type"] == "image":
            image_item: dict[str, Any] = {"type": "input_image"}
            if block["file_id"]:
                image_item["file_id"] = block["file_id"]
            elif block["url"]:
                image_item["image_url"] = block["url"]
            else:
                image_item["image_url"] = _data_url(block["mime_type"], block["data"])
            result.append(image_item)
            continue

        file_item: dict[str, Any] = {"type": "input_file"}
        if block["file_id"]:
            file_item["file_id"] = block["file_id"]
        else:
            filename = block["filename"] or _default_filename(block["mime_type"])
            file_item["filename"] = filename
            if block["url"]:
                file_item["file_url"] = block["url"]
            elif block["file_uri"]:
                file_item["file_url"] = block["file_uri"]
            else:
                file_item["file_data"] = _data_url(block["mime_type"], block["data"])
        result.append(file_item)
    return result


def _data_url(mime_type: str | None, data: str | None) -> str:
    return f"data:{mime_type or 'application/octet-stream'};base64,{data or ''}"


def _default_filename(mime_type: str | None) -> str:
    extension = mimetype_to_extension(mime_type)
    return f"attachment{extension}"


def mimetype_to_extension(mime_type: str | None) -> str:
    if not mime_type:
        return ""
    return os.path.splitext(mime_type.replace("/", "."))[1]
