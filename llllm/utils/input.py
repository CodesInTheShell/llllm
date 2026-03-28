"""Helpers for handling simple and structured user inputs."""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any

from llllm.exceptions import InvalidInputError


InputPayload = str | dict[str, Any] | list[dict[str, Any]]


def ensure_input_payload(input_data: InputPayload) -> InputPayload:
    """Validate the top-level input shape accepted by the public client."""

    if isinstance(input_data, str):
        return input_data

    if isinstance(input_data, dict):
        _validate_message(input_data)
        return input_data

    if isinstance(input_data, list):
        for item in input_data:
            if not isinstance(item, dict):
                raise InvalidInputError(
                    "Structured input lists must contain message dictionaries."
                )
            _validate_message(item)
        return input_data

    raise InvalidInputError(
        "Input must be a string, a message dictionary, or a list of message dictionaries."
    )


def ensure_plain_text_prompt(input_data: InputPayload) -> str:
    """Require a plain text prompt for providers that do not support structured input."""

    if isinstance(input_data, str):
        return input_data

    raise InvalidInputError(
        "This provider currently supports only plain text string input."
    )


def coerce_to_message_list(input_data: InputPayload) -> list[dict[str, Any]]:
    """Normalize string or single-message input into a message list."""

    if isinstance(input_data, str):
        return [{"role": "user", "content": input_data}]

    if isinstance(input_data, dict):
        return [input_data]

    return input_data


def normalize_content_blocks(content: str | list[Any]) -> list[dict[str, Any]]:
    """Convert message content into normalized content blocks."""

    if isinstance(content, str):
        return [{"type": "text", "text": content}]

    normalized: list[dict[str, Any]] = []
    for part in content:
        if not isinstance(part, dict):
            raise InvalidInputError("Content part entries must be dictionaries.")

        part_type = part.get("type")
        if part_type is None and "text" in part:
            part_type = "text"

        if part_type == "text":
            text = part.get("text")
            if not isinstance(text, str):
                raise InvalidInputError("Text content parts require a string 'text'.")
            normalized.append({"type": "text", "text": text})
            continue

        if part_type in {"image", "file"}:
            normalized.append(_normalize_binary_part(part, part_type))
            continue

        raise InvalidInputError(
            "Content part 'type' must be one of: text, image, file."
        )

    return normalized


def split_system_messages(
    messages: list[dict[str, Any]],
    explicit_system: str | None,
) -> tuple[str | None, list[dict[str, Any]]]:
    """Extract string system prompts for providers that use top-level system fields."""

    system_parts: list[str] = []
    non_system_messages: list[dict[str, Any]] = []

    if explicit_system:
        system_parts.append(explicit_system)

    for message in messages:
        role = message["role"]
        content = message["content"]
        if role == "system":
            if isinstance(content, str):
                system_parts.append(content)
            else:
                raise InvalidInputError(
                    "System message content must be a string for this provider."
                )
            continue
        non_system_messages.append(message)

    return ("\n\n".join(system_parts) if system_parts else None), non_system_messages


def _validate_message(message: dict[str, Any]) -> None:
    if "role" not in message or "content" not in message:
        raise InvalidInputError(
            "Structured message dictionaries must include 'role' and 'content'."
        )

    role = message["role"]
    content = message["content"]

    if not isinstance(role, str) or not role.strip():
        raise InvalidInputError("Message 'role' must be a non-empty string.")

    if not isinstance(content, (str, list)):
        raise InvalidInputError("Message 'content' must be a string or a list.")

    if isinstance(content, list):
        normalize_content_blocks(content)


def _normalize_binary_part(part: dict[str, Any], part_type: str) -> dict[str, Any]:
    mime_type = part.get("mime_type")
    filename = part.get("filename")
    data = part.get("data")
    path = part.get("path")
    url = part.get("url")
    file_id = part.get("file_id")
    file_uri = part.get("file_uri")

    if path is not None:
        resolved = _load_file_part(path, mime_type=mime_type)
        data = resolved["data"]
        mime_type = resolved["mime_type"]
        filename = filename or resolved["filename"]

    if data is not None:
        if not isinstance(data, str):
            raise InvalidInputError("Binary part 'data' must be a base64 string.")
        if not isinstance(mime_type, str) or not mime_type:
            raise InvalidInputError(
                "Binary parts with inline data require a 'mime_type'."
            )

    if url is not None and not isinstance(url, str):
        raise InvalidInputError("Binary part 'url' must be a string.")
    if file_id is not None and not isinstance(file_id, str):
        raise InvalidInputError("Binary part 'file_id' must be a string.")
    if file_uri is not None and not isinstance(file_uri, str):
        raise InvalidInputError("Binary part 'file_uri' must be a string.")
    if filename is not None and not isinstance(filename, str):
        raise InvalidInputError("Binary part 'filename' must be a string.")

    if not any([data, url, file_id, file_uri]):
        raise InvalidInputError(
            f"{part_type.title()} parts require one of: data, path, url, file_id, file_uri."
        )

    return {
        "type": part_type,
        "mime_type": mime_type,
        "filename": filename,
        "data": data,
        "url": url,
        "file_id": file_id,
        "file_uri": file_uri,
    }


def _load_file_part(path_value: Any, *, mime_type: str | None) -> dict[str, str]:
    if not isinstance(path_value, str):
        raise InvalidInputError("Binary part 'path' must be a string.")

    path = Path(path_value).expanduser()
    try:
        raw_bytes = path.read_bytes()
    except OSError as exc:
        raise InvalidInputError(f"Could not read file at path '{path_value}': {exc}") from exc

    detected_mime_type = mime_type or mimetypes.guess_type(path.name)[0]
    if detected_mime_type is None:
        detected_mime_type = "application/octet-stream"

    return {
        "data": base64.b64encode(raw_bytes).decode("ascii"),
        "mime_type": detected_mime_type,
        "filename": path.name,
    }
