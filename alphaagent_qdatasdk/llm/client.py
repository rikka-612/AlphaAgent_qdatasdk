"""Small chat client with Kimi Coding compatibility support."""

from __future__ import annotations

import json
from typing import Any
from urllib import error, request

from alphaagent_qdatasdk.llm.config import LLMConfig


class LLMClient:
    """HTTP chat client that keeps provider compatibility logic centralized."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Send a chat completion request and return the raw JSON payload."""

        body: dict[str, Any] = {
            "model": self.config.resolved_model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            body["max_tokens"] = max_tokens

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        headers.update(self.config.resolved_headers)

        url = f"{self.config.resolved_api_base}/chat/completions"
        payload = json.dumps(body).encode("utf-8")
        req = request.Request(url, data=payload, headers=headers, method="POST")

        try:
            with request.urlopen(req, timeout=self.config.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Chat completion failed with HTTP {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Chat completion failed: {exc.reason}") from exc

    def chat_text(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> str:
        """Return the assistant text content from a chat completion."""

        payload = self.chat_completion(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        choices = payload.get("choices") or []
        if not choices:
            raise RuntimeError("Chat completion returned no choices.")
        message = choices[0].get("message") or {}
        content = message.get("content", "")
        if not content:
            content = message.get("reasoning_content", "")
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
                else:
                    parts.append(str(item))
            return "".join(parts)
        return str(content)

    def chat_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Return a JSON object produced by the model."""

        text = self.chat_text(
            system_prompt=system_prompt + "\nReturn valid JSON only. Do not use markdown fences.",
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        try:
            return _parse_json_object(text)
        except (RuntimeError, json.JSONDecodeError):
            return {"_raw_text": text}


def _parse_json_object(text: str) -> dict[str, Any]:
    cleaned = _strip_code_fences(text.strip())
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        try:
            parsed = json.loads(_extract_json_fragment(cleaned))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Could not parse JSON object from LLM response: {text}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("Expected a JSON object from the LLM response.")
    return parsed


def _strip_code_fences(text: str) -> str:
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _extract_json_fragment(text: str) -> str:
    start = text.find("{")
    if start == -1:
        raise RuntimeError(f"Could not find JSON object in LLM response: {text}")

    opening = "{"
    closing = "}"
    depth = 0
    for idx in range(start, len(text)):
        char = text[idx]
        if char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return text[start : idx + 1]
    raise RuntimeError(f"Could not extract a balanced JSON object from: {text}")
