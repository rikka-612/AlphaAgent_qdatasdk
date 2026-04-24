"""Prompts for feedback generation."""

from __future__ import annotations

import json
from string import Template
from typing import Any

from alphaagent_qdatasdk.prompts.loader import load_prompt_yaml


_PROMPT_CONFIG = load_prompt_yaml("feedback")

FEEDBACK_SYSTEM_PROMPT = _PROMPT_CONFIG["system_prompt"]
_FEEDBACK_USER_TEMPLATE = Template(_PROMPT_CONFIG["user_prompt_template"])


def build_feedback_user_prompt(
    *,
    hypothesis: str,
    performance_summary: dict[str, Any],
    sota_comparison: dict[str, Any],
    trace_summary: str,
) -> str:
    return _FEEDBACK_USER_TEMPLATE.safe_substitute(
        hypothesis=hypothesis,
        performance_summary_json=json.dumps(performance_summary, ensure_ascii=False),
        sota_comparison_json=json.dumps(sota_comparison, ensure_ascii=False),
        trace_summary=trace_summary,
    )
