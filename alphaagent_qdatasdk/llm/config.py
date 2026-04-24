"""Provider-aware LLM configuration helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


KIMI_CODING_BASE = "https://api.kimi.com/coding/v1"
KIMI_CODING_MODEL = "openai/kimi-for-coding"
KIMI_CODING_USER_AGENT = "KimiCLI/0.77"
KIMI_MODEL_ALIASES = {
    "kimi-for-coding",
    "openai/kimi-for-coding",
    "openai/kimi-k2.6",
    "kimi-k2.6",
    "moonshot/k2.6",
}


def is_kimi_code_chat(model_name: str | None, api_base: str | None) -> bool:
    """Return whether the request should use the Kimi coding compatibility path."""

    model = (model_name or "").lower()
    base = (api_base or "").rstrip("/").lower()
    if base.startswith("https://api.kimi.com/coding"):
        return True
    return any(alias in model for alias in KIMI_MODEL_ALIASES)


def normalize_chat_model(model_name: str | None, api_base: str | None) -> str | None:
    """Normalize chat model names for provider-specific compatibility."""

    if model_name is None and is_kimi_code_chat(model_name, api_base):
        return KIMI_CODING_MODEL
    if model_name is None:
        return None
    if is_kimi_code_chat(model_name, api_base):
        return KIMI_CODING_MODEL
    return model_name


def resolve_chat_api_base(api_base: str | None, model_name: str | None) -> str:
    """Resolve the final API base used for chat completions."""

    if is_kimi_code_chat(model_name, api_base):
        return KIMI_CODING_BASE
    return (api_base or "https://api.openai.com/v1").rstrip("/")


def get_provider_headers(model_name: str | None, api_base: str | None) -> dict[str, str]:
    """Return provider-specific headers for the outgoing chat request."""

    if is_kimi_code_chat(model_name, api_base):
        return {"User-Agent": KIMI_CODING_USER_AGENT}
    return {}


@dataclass(slots=True)
class LLMConfig:
    """Resolved LLM configuration used by the project."""

    api_key: str
    api_base: str
    model: str
    timeout: float = 60.0
    extra_headers: dict[str, str] = field(default_factory=dict)

    @property
    def resolved_api_base(self) -> str:
        return resolve_chat_api_base(self.api_base, self.model)

    @property
    def resolved_model(self) -> str:
        return normalize_chat_model(self.model, self.api_base) or self.model

    @property
    def resolved_headers(self) -> dict[str, str]:
        headers = dict(self.extra_headers)
        headers.update(get_provider_headers(self.model, self.api_base))
        return headers


def build_llm_config(*, required: bool = False) -> LLMConfig | None:
    """Build LLM config from local environment variables."""

    api_key = os.getenv("ALPHAAGENT_LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        if required:
            raise ValueError("Missing ALPHAAGENT_LLM_API_KEY / OPENAI_API_KEY.")
        return None

    api_base = (
        os.getenv("ALPHAAGENT_LLM_API_BASE")
        or os.getenv("OPENAI_BASE_URL")
        or os.getenv("OPENAI_API_BASE")
        or KIMI_CODING_BASE
    )
    model = os.getenv("ALPHAAGENT_LLM_MODEL") or os.getenv("OPENAI_MODEL") or KIMI_CODING_MODEL
    timeout_raw = os.getenv("ALPHAAGENT_LLM_TIMEOUT", "60")
    timeout = float(timeout_raw)

    return LLMConfig(
        api_key=api_key,
        api_base=api_base,
        model=model,
        timeout=timeout,
    )
