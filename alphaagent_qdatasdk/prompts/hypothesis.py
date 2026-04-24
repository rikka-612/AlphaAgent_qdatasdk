"""Prompts for hypothesis generation."""

from __future__ import annotations

import json
from string import Template
from typing import Any

from alphaagent_qdatasdk.prompts.loader import load_prompt_yaml


_PROMPT_CONFIG = load_prompt_yaml("hypothesis")

HYPOTHESIS_SYSTEM_PROMPT = _PROMPT_CONFIG["system_prompt"]
_HYPOTHESIS_USER_TEMPLATE = Template(_PROMPT_CONFIG["user_prompt_template"])


def build_hypothesis_user_prompt(
    *,
    active_direction: str,
    scenario: dict[str, Any],
    trace_summary: str,
) -> str:
    return _HYPOTHESIS_USER_TEMPLATE.safe_substitute(
        active_direction=active_direction,
        scenario_json=json.dumps(scenario, ensure_ascii=False),
        trace_summary=trace_summary,
    )
