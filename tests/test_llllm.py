import os
import tempfile
import unittest
from unittest.mock import patch

from llllm import LLLLM
from llllm.exceptions import InvalidInputError, ProviderConfigurationError
from llllm.providers.claude import ClaudeProvider
from llllm.providers.gemini import GeminiProvider
from llllm.providers.ollama import OllamaProvider
from llllm.providers.openai import OpenAIProvider
from llllm.utils.config import parse_model_spec, resolve_api_key


class ConfigTests(unittest.TestCase):
    def test_parse_model_spec(self):
        provider, model = parse_model_spec("openai:gpt-4.1")
        self.assertEqual(provider, "openai")
        self.assertEqual(model, "gpt-4.1")

    def test_parse_model_spec_rejects_invalid_provider(self):
        with self.assertRaises(ProviderConfigurationError):
            parse_model_spec("unknown:model")

    def test_resolve_api_key_prefers_explicit_value(self):
        self.assertEqual(resolve_api_key("openai", "explicit"), "explicit")

    @patch.dict(os.environ, {"OPENAI_API_KEY": "env-key"}, clear=False)
    def test_resolve_api_key_from_environment(self):
        self.assertEqual(resolve_api_key("openai", None), "env-key")


class ClientTests(unittest.TestCase):
    def test_client_selects_provider(self):
        client = LLLLM("ollama:llama3")
        self.assertEqual(client.provider.provider_name, "ollama")
        self.assertEqual(client.provider.model, "llama3")

    def test_client_rejects_invalid_structured_input_type(self):
        client = LLLLM("openai:gpt-4.1", api_key="key")
        with self.assertRaises(InvalidInputError):
            client.gen(123)  # type: ignore[arg-type]


class ProviderNormalizationTests(unittest.TestCase):
    def test_openai_build_payload_accepts_message_list(self):
        provider = OpenAIProvider(
            model="gpt-4.1",
            api_key="key",
            timeout=10,
            base_url=None,
            headers=None,
        )
        payload = provider.build_payload(
            [
                {"role": "system", "content": "You are an analyst."},
                {"role": "user", "content": "Explain OSINT."},
            ]
        )
        self.assertEqual(payload["input"][0]["role"], "system")
        self.assertEqual(payload["input"][1]["content"][0]["text"], "Explain OSINT.")

    def test_openai_build_payload_supports_inline_file_part(self):
        provider = OpenAIProvider(
            model="gpt-4.1",
            api_key="key",
            timeout=10,
            base_url=None,
            headers=None,
        )
        payload = provider.build_payload(
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this PDF."},
                    {
                        "type": "file",
                        "mime_type": "application/pdf",
                        "filename": "report.pdf",
                        "data": "ZmFrZQ==",
                    },
                ],
            }
        )
        self.assertEqual(payload["input"][0]["content"][1]["type"], "input_file")
        self.assertIn("data:application/pdf;base64,ZmFrZQ==", payload["input"][0]["content"][1]["file_data"])

    def test_claude_build_payload_splits_system_message(self):
        provider = ClaudeProvider(
            model="claude-3-7-sonnet",
            api_key="key",
            timeout=10,
            base_url=None,
            headers=None,
        )
        payload = provider.build_payload(
            [
                {"role": "system", "content": "You are an analyst."},
                {"role": "user", "content": "Explain OSINT."},
            ]
        )
        self.assertEqual(payload["system"], "You are an analyst.")
        self.assertEqual(payload["messages"], [{"role": "user", "content": "Explain OSINT."}])

    def test_gemini_build_payload_accepts_message_dict(self):
        provider = GeminiProvider(
            model="gemini-1.5-pro",
            api_key="key",
            timeout=10,
            base_url=None,
            headers=None,
        )
        payload = provider.build_payload(
            {"role": "user", "content": "Explain OSINT."}
        )
        self.assertEqual(payload["contents"][0]["role"], "user")
        self.assertEqual(payload["contents"][0]["parts"][0]["text"], "Explain OSINT.")

    def test_claude_build_payload_supports_image_part(self):
        provider = ClaudeProvider(
            model="claude-3-7-sonnet",
            api_key="key",
            timeout=10,
            base_url=None,
            headers=None,
        )
        payload = provider.build_payload(
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this image."},
                    {
                        "type": "image",
                        "mime_type": "image/png",
                        "data": "ZmFrZQ==",
                    },
                ],
            }
        )
        image_block = payload["messages"][0]["content"][1]
        self.assertEqual(image_block["type"], "image")
        self.assertEqual(image_block["source"]["type"], "base64")
        self.assertEqual(image_block["source"]["media_type"], "image/png")

    def test_gemini_build_payload_supports_inline_file_part(self):
        provider = GeminiProvider(
            model="gemini-1.5-pro",
            api_key="key",
            timeout=10,
            base_url=None,
            headers=None,
        )
        payload = provider.build_payload(
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this file."},
                    {
                        "type": "file",
                        "mime_type": "application/pdf",
                        "data": "ZmFrZQ==",
                    },
                ],
            }
        )
        inline_data = payload["contents"][0]["parts"][1]["inline_data"]
        self.assertEqual(inline_data["mime_type"], "application/pdf")
        self.assertEqual(inline_data["data"], "ZmFrZQ==")

    def test_ollama_supports_image_part(self):
        provider = OllamaProvider(
            model="llama3",
            api_key=None,
            timeout=10,
            base_url=None,
            headers=None,
        )
        payload = provider.build_payload(
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this image."},
                    {
                        "type": "image",
                        "mime_type": "image/png",
                        "data": "ZmFrZQ==",
                    },
                ],
            }
        )
        self.assertEqual(payload["messages"][0]["images"], ["ZmFrZQ=="])

    def test_ollama_rejects_non_image_file_part(self):
        provider = OllamaProvider(
            model="llama3",
            api_key=None,
            timeout=10,
            base_url=None,
            headers=None,
        )
        with self.assertRaises(InvalidInputError):
            provider.build_payload(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "file",
                            "mime_type": "application/pdf",
                            "data": "ZmFrZQ==",
                        }
                    ],
                }
            )

    def test_local_file_path_is_loaded_into_base64(self):
        with tempfile.NamedTemporaryFile(suffix=".txt") as tmp:
            tmp.write(b"hello")
            tmp.flush()
            provider = GeminiProvider(
                model="gemini-1.5-pro",
                api_key="key",
                timeout=10,
                base_url=None,
                headers=None,
            )
            payload = provider.build_payload(
                {
                    "role": "user",
                    "content": [
                        {"type": "file", "path": tmp.name},
                    ],
                }
            )
            inline_data = payload["contents"][0]["parts"][0]["inline_data"]
            self.assertEqual(inline_data["data"], "aGVsbG8=")

    def test_openai_normalization(self):
        provider = OpenAIProvider(
            model="gpt-4.1",
            api_key="key",
            timeout=10,
            base_url=None,
            headers=None,
        )
        normalized = provider.normalize_response(
            {
                "output": [{"content": [{"text": "hello"}]}],
                "usage": {"input_tokens": 5, "output_tokens": 7},
                "status": "completed",
            }
        )
        self.assertEqual(normalized["text"], "hello")
        self.assertEqual(normalized["usage"]["total_tokens"], 12)
        self.assertEqual(normalized["finish_reason"], "completed")

    def test_claude_normalization(self):
        provider = ClaudeProvider(
            model="claude-3-7-sonnet",
            api_key="key",
            timeout=10,
            base_url=None,
            headers=None,
        )
        normalized = provider.normalize_response(
            {
                "content": [{"type": "text", "text": "hello"}],
                "usage": {"input_tokens": 4, "output_tokens": 6},
                "stop_reason": "end_turn",
            }
        )
        self.assertEqual(normalized["text"], "hello")
        self.assertEqual(normalized["usage"]["total_tokens"], 10)
        self.assertEqual(normalized["finish_reason"], "end_turn")

    def test_gemini_normalization(self):
        provider = GeminiProvider(
            model="gemini-1.5-pro",
            api_key="key",
            timeout=10,
            base_url=None,
            headers=None,
        )
        normalized = provider.normalize_response(
            {
                "candidates": [
                    {
                        "content": {"parts": [{"text": "hello"}]},
                        "finishReason": "STOP",
                    }
                ],
                "usageMetadata": {
                    "promptTokenCount": 3,
                    "candidatesTokenCount": 5,
                },
            }
        )
        self.assertEqual(normalized["text"], "hello")
        self.assertEqual(normalized["usage"]["total_tokens"], 8)
        self.assertEqual(normalized["finish_reason"], "STOP")

    def test_ollama_normalization(self):
        provider = OllamaProvider(
            model="llama3",
            api_key=None,
            timeout=10,
            base_url=None,
            headers=None,
        )
        normalized = provider.normalize_response(
            {
                "response": "hello",
                "prompt_eval_count": 2,
                "eval_count": 4,
                "done_reason": "stop",
            }
        )
        self.assertEqual(normalized["text"], "hello")
        self.assertEqual(normalized["usage"]["total_tokens"], 6)
        self.assertEqual(normalized["finish_reason"], "stop")


if __name__ == "__main__":
    unittest.main()
