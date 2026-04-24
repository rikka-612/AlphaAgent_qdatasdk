"""LLM connectivity checks."""

from __future__ import annotations

from alphaagent_qdatasdk.llm import LLMClient, build_llm_config, load_local_env
from alphaagent_qdatasdk.prompts import HEALTH_CHECK_SYSTEM_PROMPT, HEALTH_CHECK_USER_PROMPT


def run_health_check() -> dict[str, str]:
    """Run the minimal chat completion check using the formal client logic."""

    load_local_env()
    config = build_llm_config(required=True)
    assert config is not None
    client = LLMClient(config)
    reply = client.chat_text(
        system_prompt=HEALTH_CHECK_SYSTEM_PROMPT,
        user_prompt=HEALTH_CHECK_USER_PROMPT,
        temperature=0.0,
    )
    return {
        "api_base": config.resolved_api_base,
        "model": config.resolved_model,
        "user_agent": config.resolved_headers.get("User-Agent", ""),
        "reply": reply.strip(),
    }
