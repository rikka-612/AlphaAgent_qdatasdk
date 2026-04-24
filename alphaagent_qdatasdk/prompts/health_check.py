"""Prompts for LLM connectivity health checks."""

from __future__ import annotations

from alphaagent_qdatasdk.prompts.loader import load_prompt_yaml


_PROMPT_CONFIG = load_prompt_yaml("health_check")

HEALTH_CHECK_SYSTEM_PROMPT = _PROMPT_CONFIG["system_prompt"]
HEALTH_CHECK_USER_PROMPT = _PROMPT_CONFIG["user_prompt"]
