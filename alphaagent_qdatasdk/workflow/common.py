"""Shared helpers for workflow stages."""

from __future__ import annotations

import json
from typing import Any

from alphaagent_qdatasdk.core import (
    FactorQualityScore,
    FeedbackDecision,
    Trace,
)


def trace_summary(trace: Trace) -> str:
    latest = trace.latest_round()
    if latest is None:
        return "No previous rounds."
    return (
        f"Latest round={latest.round_id}; "
        f"decision={latest.feedback.decision.value}; "
        f"status={latest.result.status.value}; "
        f"hypothesis={latest.hypothesis.hypothesis}"
    )


def as_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []


def optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def parse_feedback_decision(value: Any) -> FeedbackDecision:
    try:
        return FeedbackDecision(str(value).strip().lower())
    except ValueError:
        return FeedbackDecision.REFINE


def is_feedback_decision(value: Any) -> bool:
    try:
        FeedbackDecision(str(value).strip().lower())
    except ValueError:
        return False
    return True


def build_quality_score(value: Any) -> FactorQualityScore | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        return FactorQualityScore(
            scorer_name="llm-feedback",
            score_version="draft",
            rationale="LLM returned a non-dict quality score payload.",
            details={"raw_quality_score": value},
        )
    raw_score = value.get("overall_score")
    try:
        overall_score = None if raw_score is None else float(raw_score)
    except (TypeError, ValueError):
        overall_score = None
    details = value.get("details")
    return FactorQualityScore(
        overall_score=overall_score,
        score_scale=str(value.get("score_scale", "unplanned")),
        scorer_name=str(value.get("scorer_name", "llm-feedback")),
        score_version=str(value.get("score_version", "draft")),
        rationale=str(value.get("rationale", "")).strip(),
        details=details if isinstance(details, dict) else {"raw_details": details},
    )


def summarize_text(text: str, limit: int) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def has_required_strings(payload: dict[str, Any], keys: list[str]) -> bool:
    return all(str(payload.get(key, "")).strip() for key in keys)


def payload_to_text(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)
