"""Workflow output models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from alphaagent_qdatasdk.core import (
    AlphaAgentHypothesis,
    ExperimentResult,
    FactorExperiment,
    HypothesisFeedback,
)


@dataclass(slots=True)
class LoopRoundOutput:
    """Structured output for one loop round."""

    round_id: int
    hypothesis: AlphaAgentHypothesis
    experiment: FactorExperiment
    sub_workspace_list: list[Path]
    result: ExperimentResult
    feedback: HypothesisFeedback
