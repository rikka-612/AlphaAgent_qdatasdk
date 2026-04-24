"""Trace update stage."""

from __future__ import annotations

from dataclasses import dataclass

from alphaagent_qdatasdk.core import (
    AlphaAgentHypothesis,
    ExperimentResult,
    FactorExperiment,
    HypothesisFeedback,
    RoundRecord,
    Trace,
)


@dataclass(slots=True)
class TraceStage:
    """Append round records and maintain trace-level state."""

    def update(
        self,
        trace: Trace,
        hypothesis: AlphaAgentHypothesis,
        experiment: FactorExperiment,
        result: ExperimentResult,
        feedback: HypothesisFeedback,
        round_id: int,
    ) -> None:
        record = RoundRecord(
            round_id=round_id,
            hypothesis=hypothesis,
            experiment=experiment,
            result=result,
            feedback=feedback,
        )
        trace.append_round(record)
        if result.succeeded and trace.current_sota is None:
            trace.set_current_sota(result)
