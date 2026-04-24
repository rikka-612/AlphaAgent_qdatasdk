"""Prompts for experiment generation."""

from __future__ import annotations

import json
from string import Template
from typing import Any

from alphaagent_qdatasdk.prompts.loader import load_prompt_yaml


_PROMPT_CONFIG = load_prompt_yaml("experiment")

EXPERIMENT_SYSTEM_PROMPT = _PROMPT_CONFIG["system_prompt"]
_EXPERIMENT_USER_TEMPLATE = Template(_PROMPT_CONFIG["user_prompt_template"])


def build_experiment_user_prompt(
    *,
    hypothesis: str,
    scenario: dict[str, Any],
    trace_summary: str,
) -> str:
    return _EXPERIMENT_USER_TEMPLATE.safe_substitute(
        hypothesis=hypothesis,
        scenario_json=json.dumps(scenario, ensure_ascii=False),
        trace_summary=trace_summary,
    )
