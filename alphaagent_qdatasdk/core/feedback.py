"""Feedback contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from alphaagent_qdatasdk.core.enums import FeedbackDecision
from alphaagent_qdatasdk.core.types import JsonDict


@dataclass(slots=True)
class FactorQualityScore:
    """Flexible quality score container for factor evaluation.

    The scoring dimensions are intentionally not fixed yet. Future scoring
    mechanisms can store detailed sub-scores, formulas, thresholds, and
    diagnostics in ``details`` without changing the feedback contract.
    """

    overall_score: float | None = None
    score_scale: str = "unplanned"
    scorer_name: str = "unplanned"
    score_version: str = "draft"
    rationale: str = ""
    details: JsonDict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class HypothesisFeedback:
    """Structured judgment from result analysis back to the research loop."""

    observations: str
    hypothesis_evaluation: str
    decision: FeedbackDecision
    reason: str
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    next_direction: str | None = None
    new_hypothesis: str | None = None
    quality_score: FactorQualityScore | None = None

    @property
    def should_continue(self) -> bool:
        return self.decision in {
            FeedbackDecision.CONTINUE,
            FeedbackDecision.REFINE,
            FeedbackDecision.BRANCH,
        }
