"""Helpers for shaping standardized responses."""

from __future__ import annotations

from typing import Any


def build_response(
    *,
    raw_response: dict[str, Any],
    provider: str,
    model: str,
    normalized: dict[str, Any],
) -> dict[str, Any]:
    """Wrap normalized provider output in the public response schema."""

    llllm_response = {
        "text": normalized.get("text", ""),
        "provider": provider,
        "model": model,
        "usage": normalized.get(
            "usage",
            {
                "input_tokens": None,
                "output_tokens": None,
                "total_tokens": None,
            },
        ),
        "finish_reason": normalized.get("finish_reason"),
    }
    return {
        "raw_response": raw_response,
        "llllm_response": llllm_response,
    }
