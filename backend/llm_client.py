"""
LLM Client — provider-agnostic interface.

Default: DeepSeek (deepseek-flash for normal, deepseek-v4-pro for ultra).
Also supports: Gemini, OpenAI, Anthropic.
Configure with LLM_PROVIDER and LLM_MODEL env vars.

Every module imports: client, _extract_json, PRIMARY_MODEL, FALLBACK_MODEL, ULTRA_MODEL.
"""

import os
import re
import json
import time
import logging
from typing import Optional

import requests

log = logging.getLogger(__name__)

# ── Model configuration ──
PRIMARY_MODEL = os.environ.get("LLM_MODEL", "deepseek-v4-flash").strip()
ANALYTICAL_MODEL = os.environ.get("LLM_MODEL_ANALYTICAL", "deepseek-v4-flash").strip()
ULTRA_MODEL = os.environ.get("LLM_MODEL_ULTRA", "deepseek-v4-pro").strip()
FALLBACK_MODEL = os.environ.get("LLM_MODEL_FALLBACK", "deepseek-v4-flash").strip()


# ── JSON extraction utility ──

def _extract_json(txt: str) -> str:
    """Pull the first balanced JSON object out of a model reply.
    Tolerates code fences, leading prose, and trailing prose."""
    s = re.sub(r"^```(json)?|```$", "", txt or "", flags=re.M).strip()
    start = s.find("{")
    if start == -1:
        return s
    depth, in_str, esc = 0, False, False
    for i in range(start, len(s)):
        c = s[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return s[start:i + 1]
    return s[start:]

# ── Unified response types (Anthropic-compatible shape) ──

class ContentBlock:
    __slots__ = ("text", "type")
    def __init__(self, text: str):
        self.text = text
        self.type = "text"

class Usage:
    __slots__ = ("input_tokens", "output_tokens")
    def __init__(self, input_tokens: int = 0, output_tokens: int = 0):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens

class Response:
    __slots__ = ("content", "usage", "function_call")
    def __init__(self, text: str = "", input_tokens: int = 0, output_tokens: int = 0,
                 function_call: dict = None):
        self.content = [ContentBlock(text)]
        self.usage = Usage(input_tokens, output_tokens)
        self.function_call = function_call


# ── Abstract provider interface ──

class _BaseProvider:
    """Every provider implements .create(model, system, messages, max_tokens, tools, **kwargs) → Response."""
    def create(self, model: str, system=None, messages=None, max_tokens=None, tools=None, **kwargs) -> Response:
        raise NotImplementedError


# ── Gemini provider ──

_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

class GeminiProvider(_BaseProvider):
    def __init__(self, api_key: str):
        self._api_key = api_key
        self._session = requests.Session()
        self._session.headers.update({"x-goog-api-key": api_key, "Content-Type": "application/json"})

    def _url(self, model: str) -> str:
        return f"{_GEMINI_BASE}/{model}:generateContent"

    @staticmethod
    def _system_to_text(system) -> Optional[str]:
        if not system:
            return None
        if isinstance(system, str):
            return system
        if isinstance(system, list):
            texts = [s["text"] for s in system if isinstance(s, dict) and isinstance(s.get("text"), str) and s["text"].strip()]
            return "\n".join(texts) if texts else None
        return None

    @staticmethod
    def _convert_content(content):
        if isinstance(content, str):
            return [{"text": content}]
        parts = []
        for block in content:
            if not isinstance(block, dict):
                parts.append({"text": str(block)})
                continue
            t = block.get("type", "")
            if t == "text":
                parts.append({"text": block.get("text", "")})
            elif t == "image":
                src = block.get("source", {})
                if src.get("type") == "base64":
                    parts.append({"inline_data": {"mime_type": src.get("media_type", "image/png"), "data": src.get("data", "")}})
                elif src.get("type") == "url":
                    parts.append({"file_data": {"file_uri": src["url"], "mime_type": src.get("media_type", "image/png")}})
        return parts

    def create(self, model: str, system=None, messages=None, max_tokens=None, tools=None, **kwargs) -> Response:
        system_text = self._system_to_text(system)
        contents = []
        for m in messages or []:
            role = "model" if m.get("role") == "assistant" else "user"
            parts = self._convert_content(m.get("content", ""))
            contents.append({"role": role, "parts": parts})

        body = {"contents": contents, "generationConfig": {"maxOutputTokens": max_tokens or 8192}}
        if system_text:
            body["system_instruction"] = {"parts": [{"text": system_text}]}
        if tools and isinstance(tools, list):
            body["tools"] = [{"functionDeclarations": tools}]
            body["toolConfig"] = {"functionCallingConfig": {"mode": "AUTO"}}

        last_err = None
        for attempt in range(4):
            resp = None
            try:
                resp = self._session.post(self._url(model), json=body, timeout=120)
                resp.raise_for_status()
            except requests.exceptions.RequestException as e:
                detail = ""
                try:
                    if resp is not None:
                        detail = resp.text
                except Exception:
                    pass
                status = resp.status_code if resp is not None and hasattr(resp, 'status_code') else 0
                should_retry = attempt < 3 and (status in (429, 503) or resp is None)
                if should_retry:
                    delay = 2 ** attempt * 3
                    log.warning(f"LLM retry {attempt+1}/3 after {delay:.0f}s: status={status}")
                    time.sleep(delay)
                    last_err = RuntimeError(f"LLM API error: {e} {detail[:300]}")
                    continue
                raise RuntimeError(f"LLM API error: {e} {detail[:500]}")

            data = resp.json()
            text = ""
            function_call = None
            candidates = data.get("candidates") or []
            if candidates:
                c = candidates[0]
                finish = c.get("finishReason", "")
                if finish in ("SAFETY", "BLOCKLIST", "PROHIBITED_CONTENT"):
                    log.warning(f"LLM blocked: finishReason={finish}")
                parts = (c.get("content") or {}).get("parts") or []
                for part in parts:
                    if "text" in part:
                        text += part.get("text", "")
                    if "functionCall" in part:
                        fc = part["functionCall"]
                        function_call = {"name": fc.get("name", ""), "args": fc.get("args", {})}

            usage = data.get("usageMetadata") or {}
            return Response(text, usage.get("promptTokenCount", 0) or 0, usage.get("candidatesTokenCount", 0) or 0, function_call)

        raise last_err or RuntimeError("LLM API failed after retries")


# ── DeepSeek / OpenAI-compatible provider ──

class OpenAICompatibleProvider(_BaseProvider):
    def __init__(self, api_key: str, base_url: str):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update({"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})

    @staticmethod
    def _system_to_text(system) -> Optional[str]:
        if not system:
            return None
        if isinstance(system, str):
            return system
        if isinstance(system, list):
            texts = [s["text"] for s in system if isinstance(s, dict) and isinstance(s.get("text"), str) and s["text"].strip()]
            return "\n".join(texts) if texts else None
        return None

    def create(self, model: str, system=None, messages=None, max_tokens=None, tools=None, **kwargs) -> Response:
        msgs = []
        system_text = self._system_to_text(system)
        if system_text:
            msgs.append({"role": "system", "content": system_text})
        for m in messages or []:
            role = m.get("role", "user")
            content = m.get("content", "")
            if isinstance(content, list):
                text_parts = [b["text"] for b in content if isinstance(b, dict) and b.get("type") == "text"]
                content = "\n".join(text_parts) if text_parts else str(content)
            msgs.append({"role": role, "content": content})

        body = {"model": model, "messages": msgs, "max_tokens": max_tokens or 4096}
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"

        last_err = None
        for attempt in range(4):
            resp = None
            try:
                resp = self._session.post(f"{self._base_url}/chat/completions", json=body, timeout=120)
                resp.raise_for_status()
            except requests.exceptions.RequestException as e:
                detail = ""
                try:
                    if resp is not None:
                        detail = resp.text
                except Exception:
                    pass
                status = resp.status_code if resp is not None and hasattr(resp, 'status_code') else 0
                should_retry = attempt < 3 and (status in (429, 503) or resp is None)
                if should_retry:
                    delay = 2 ** attempt * 3
                    log.warning(f"LLM retry {attempt+1}/3 after {delay:.0f}s: status={status}")
                    time.sleep(delay)
                    last_err = RuntimeError(f"LLM API error: {e} {detail[:300]}")
                    continue
                raise RuntimeError(f"LLM API error: {e} {detail[:500]}")

            data = resp.json()
            choice = (data.get("choices") or [{}])[0]
            msg = choice.get("message", {})
            text = msg.get("content", "")
            fc = msg.get("tool_calls", [{}])[0] if msg.get("tool_calls") else None
            function_call = None
            if fc and fc.get("function"):
                try:
                    function_call = {"name": fc["function"]["name"], "args": json.loads(fc["function"]["arguments"])}
                except (json.JSONDecodeError, KeyError):
                    function_call = {"name": fc["function"]["name"], "args": fc["function"].get("arguments", "{}")}

            usage_data = data.get("usage", {})
            return Response(text, usage_data.get("prompt_tokens", 0) or 0, usage_data.get("completion_tokens", 0) or 0, function_call)

        raise last_err or RuntimeError("LLM API failed after retries")


# ── Unified client ──

class LLMClient:
    def __init__(self, provider: _BaseProvider):
        self._messages = _MessagesProxy(provider)

    @property
    def messages(self):
        return self._messages


class _MessagesProxy:
    def __init__(self, provider: _BaseProvider):
        self._provider = provider

    def create(self, model: str, system=None, messages=None, max_tokens=None, tools=None, **kwargs) -> Response:
        return self._provider.create(model=model, system=system, messages=messages,
                                      max_tokens=max_tokens, tools=tools, **kwargs)


_client: Optional[LLMClient] = None


def init_client() -> LLMClient:
    """Initialize LLM client from environment. Supports GEMINI_API_KEY (legacy) or LLM_PROVIDER."""
    global _client
    if _client is not None:
        return _client

    provider_name = os.environ.get("LLM_PROVIDER", "deepseek").strip().lower()
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()

    if provider_name == "deepseek":
        key = deepseek_key or os.environ.get("LLM_API_KEY", "")
        if not key:
            raise RuntimeError("DEEPSEEK_API_KEY or LLM_API_KEY not set")
        provider = OpenAICompatibleProvider(key, "https://api.deepseek.com/v1")
        log.info("LLM provider: DeepSeek")

    elif provider_name == "openai":
        key = openai_key or os.environ.get("LLM_API_KEY", "")
        if not key:
            raise RuntimeError("OPENAI_API_KEY or LLM_API_KEY not set")
        provider = OpenAICompatibleProvider(key, "https://api.openai.com/v1")
        log.info("LLM provider: OpenAI")

    elif provider_name == "anthropic":
        key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        provider = OpenAICompatibleProvider(key, "https://api.anthropic.com/v1")
        log.info("LLM provider: Anthropic")

    else:  # gemini (default / fallback)
        key = gemini_key or os.environ.get("LLM_API_KEY", "")
        if not key:
            raise RuntimeError("GEMINI_API_KEY or LLM_API_KEY not set")
        provider = GeminiProvider(key)
        log.info("LLM provider: Gemini")

    _client = LLMClient(provider)
    return _client


def client() -> LLMClient:
    """Get or create the global LLM client."""
    global _client
    if _client is not None:
        return _client
    return init_client()


def reset_client():
    """Reset cached client — used when switching providers at runtime."""
    global _client
    _client = None


# ── demo ──
if __name__ == "__main__":
    print("LLM Client loaded — provider:", os.environ.get("LLM_PROVIDER", "deepseek"))
    print("Primary: deepseek-flash  |  Ultra: deepseek-v4-pro")
    print("Status: OK (no API call made)")
