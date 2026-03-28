🧠 Product Documentation: LLLLM (Lightweight Local & Large Language Model Wrapper)
🚀 Overview

LLLLM is built around the three major AI providers:

- Gemini
- Claude
- OpenAI

It also includes special support for Ollama and local models.

The thinking behind the project is simple: the author believes the big three providers are already more than enough to build real AI systems and products. The dedicated support for Ollama reflects a second belief that open models will keep getting smaller and smarter, while the hardware needed to run AI models locally will keep getting cheaper.

It is also lightweight in a practical engineering sense: LLLLM uses direct HTTP requests through `requests` instead of depending on vendor SDKs. You do not need to install extra packages such as the OpenAI Python library, Anthropic SDK, or Google's Gemini client library just to call the APIs.

LLLLM is a minimal, dependency-light Python library that provides a single unified interface for interacting with:

- OpenAI via the Responses API
- Claude via the Anthropic Messages API
- Gemini via the Google Generative Language API
- Ollama for local models

It is designed to be:

- ⚡ Lightweight — only uses requests for direct API calls, without vendor SDK dependencies
- 🧩 Simple — one class, one method
- 🔄 Standardized — same output across all providers
- 🌐 Hybrid — supports both cloud and local models
🎯 Problem It Solves

Working with multiple LLM providers today means:

- Different SDKs and dependencies
- Different request/response formats
- No easy switching between providers
- Local models like Ollama require separate handling

LLLLM solves this by:

- Using direct HTTP calls without SDK lock-in
- Providing a single interface across all providers
- Standardizing outputs
- Supporting both cloud and local models in one API
🧱 Core Design Philosophy

“One client. One method. Any model — local or cloud.”

🧩 Supported Providers

| Provider | Type | Notes |
| --- | --- | --- |
| OpenAI | Cloud | Uses the Responses API |
| Claude | Cloud | Uses the Anthropic Messages API |
| Gemini | Cloud | Uses the Google Generative Language API |
| Ollama | Local | Runs on localhost |

🧩 Core Features
1. 🔌 Multi-Provider + Local Support
```python
client = LLLLM("openai:gpt-5.4")
client = LLLLM("claude:claude-sonnet-4-6")
client = LLLLM("gemini:gemini-3.1-pro-preview")
client = LLLLM("ollama:gemma3")
```
2. 🧠 Unified Generation API
```python
response = client.gen("Explain OSINT in simple terms")
```

Same call works for:

- OpenAI
- Claude
- Gemini
- Ollama

Structured role-based input is also supported for OpenAI, Claude, and Gemini:

```python
response = client.gen([
    {"role": "system", "content": "You are an OSINT analyst"},
    {"role": "user", "content": "Explain OSINT in simple terms"}
])
```

Multimodal content parts are also supported:

```python
response = client.gen([
    {
        "role": "user",
        "content": [
            {"type": "text", "text": "Describe this image"},
            {"type": "image", "path": "./image.png"}
        ]
    }
])
```

```python
response = client.gen([
    {
        "role": "user",
        "content": [
            {"type": "text", "text": "Summarize this file"},
            {"type": "file", "path": "./report.pdf"}
        ]
    }
])
```
3. 📦 Standardized Response Object

All providers return the same structure:

```python
{
    "raw_response": {...},
    "llllm_response": {
        "text": "...",
        "provider": "...",
        "model": "...",
        "usage": {
            "input_tokens": int | None,
            "output_tokens": int | None,
            "total_tokens": int | None
        },
        "finish_reason": str | None
    }
}
```
4. 🌐 Hybrid Cloud + Local Usage

Switch between cloud and local seamlessly:

```python
# Cloud
client = LLLLM("openai:gpt-5.4")

# Local
client = LLLLM("ollama:gemma3")
```

No code changes needed.

5. 🪶 Zero Heavy Dependencies

- Only dependency: `requests`
- No provider SDKs like `openai`, Anthropic SDKs, or Google Gemini client libraries
- No async frameworks
- No runtime bloat

6. 🔐 Flexible Authentication
```python
client = LLLLM("openai:gpt-5.4", api_key="your_key")
```

Or via environment variables:

```bash
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
GEMINI_API_KEY=...
LLLLM_FALLBACK_MODEL=claude:claude-sonnet-4-6
```

Ollama:

- No API key required
- Runs on `http://localhost:11434`

Fallback behavior:

- LLLLM retries a failed primary request up to 5 times.
- If all 5 attempts fail, it checks `LLLLM_FALLBACK_MODEL`.
- If that environment variable is set, it switches to the configured secondary `provider:model` and retries that target up to 5 times as well.
- If no fallback target is configured, it raises an exception instead of guessing a default secondary provider.

Why this helps:

- It gives applications a simple resilience layer when a provider has temporary outages, request instability, or rate-limit issues.
- It lets teams define their own backup provider strategy through environment configuration without hardcoding failover logic in application code.

7. ⚙️ Minimal Parameter Interface
```python
response = client.gen(
    "Write a short intelligence report",
    temperature=0.7,
    max_tokens=300,
    system="You are an OSINT analyst"
)
```

Mapped internally per provider.

Input formats currently supported:

- Simple string input for all providers
- Role-based dict input for all providers
- Role-based list input for all providers
- Structured content parts for text, image, and file inputs

Provider notes:

- OpenAI supports text, image, and file parts
- Claude supports text, image, and file/document parts
- Gemini supports text, image, and file parts
- Ollama supports text and image parts; non-image file parts are rejected

🧪 Example Usage
```python
from llllm import LLLLM

client = LLLLM("ollama:gemma3")

res = client.gen("Summarize cyber threat intelligence")

print(res["llllm_response"]["text"])
```

Fallback example:

Set:

```bash
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
LLLLM_FALLBACK_MODEL=claude:claude-sonnet-4-6
```

Then:

```python
from llllm import LLLLM

client = LLLLM("openai:gpt-5.4")
res = client.gen("Summarize cyber threat intelligence")

print(res["llllm_response"]["text"])
```

In this setup, LLLLM tries OpenAI first. If 5 attempts fail, it logs the failure, logs that the fallback is being used, and then retries against Claude up to 5 times.
🏗️ Architecture
```text
llllm/
│
├── core.py
├── providers/
│   ├── openai.py      # Responses API
│   ├── claude.py
│   ├── gemini.py
│   └── ollama.py      # local
│
├── utils/
│   ├── normalize.py
│   └── config.py
│
└── exceptions.py
```
🔄 Internal Flow
```text
User Input
   ↓
LLLLM.gen()
   ↓
Provider Adapter (openai / claude / gemini / ollama)
   ↓
HTTP Request (requests)
   ↓
Raw Response
   ↓
Normalizer
   ↓
Standardized Output
```
📏 Standardization Strategy

Each provider adapter must output:
```
{
    "text": str,
    "usage": {...},
    "finish_reason": str | None
}
```
Then wrapped into:
```
{
    "raw_response": raw,
    "llllm_response": normalized
}
```
🔧 Provider Implementation Notes
OpenAI (Responses API)
```text
Endpoint: /v1/responses
Input format:
input
optional system
Extract:
output[0].content[0].text (or equivalent)
Usage fields mapped to standard format
```
Claude
```text
Endpoint: /v1/messages
Requires:
x-api-key
anthropic-version
Message-based structure
```
Gemini
```text
REST endpoint
Uses contents.parts
Nested response parsing required
```
Ollama
```text
Endpoint: http://localhost:11434/api/chat
No API key
Fast local inference
May not return token usage → set as None
```
🧩 MVP Scope (v0.1)

Included:

- Text generation
- 4 providers: the Big 3 plus Ollama
- Standardized response format
- Sync API
- API key and environment variable support
- Primary retry plus secondary fallback via environment variable

Not included:

- Streaming
- Async
- Function or tool calling
- Image or audio generation
- Conversation memory

🗺️ Roadmap

v0.2:

- Streaming support
- Better error mapping

v0.3:

- Function or tool abstraction
- Structured outputs

v0.4:

- Async support
- Middleware and hooks

💡 Key Value Proposition

“Switch between OpenAI, Claude, Gemini, and Ollama with one line — no SDKs, no complexity.”

🧠 Taglines

- “One interface. Local + Cloud LLMs.”
- “From GPT to LLaMA — same code.”
- “Minimal wrapper for maximum flexibility.”

⚡ Design Principles

- Keep abstraction shallow
- Do not hide provider behavior unnecessarily
- Always return raw response
- Standardize only what matters
