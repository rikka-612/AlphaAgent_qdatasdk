"""Trace and round-history contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from alphaagent_qdatasdk.core.factor import FactorExperiment, FactorTask
from alphaagent_qdatasdk.core.feedback import HypothesisFeedback
from alphaagent_qdatasdk.core.hypothesis import AlphaAgentHypothesis
from alphaagent_qdatasdk.core.result import ExperimentResult


@dataclass(slots=True)
class FailedTaskRecord:
    """Append-only record for a task that failed in any workflow stage."""

    task: FactorTask
    round_id: int | None = None
    stage: str | None = None
    error_message: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class RoundRecord:
    """Append-only summary of one completed research round."""

    round_id: int
    hypothesis: AlphaAgentHypothesis
    experiment: FactorExperiment
    result: ExperimentResult
    feedback: HypothesisFeedback
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class Trace:
    """Cross-round memory for the alpha-research loop."""

    active_direction: str
    scenario: Any
    round_id: int = 0
    hist: list[RoundRecord] = field(default_factory=list)
    failed_tasks: list[FailedTaskRecord] = field(default_factory=list)
    current_sota: ExperimentResult | None = None

    def append_round(self, record: RoundRecord) -> None:
        """Append a completed round and move the trace cursor forward."""

        self.hist.append(record)
        self.round_id = record.round_id

    def latest_round(self) -> RoundRecord | None:
        """Return the most recent round record, if any."""

        if not self.hist:
            return None
        return self.hist[-1]

    def set_current_sota(self, result: ExperimentResult) -> None:
        """Record the current best result after an external comparison step."""

        self.current_sota = result

    def record_failed_task(
        self,
        task: FactorTask,
        *,
        round_id: int | None = None,
        stage: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """Append one failed task to the trace."""

        self.failed_tasks.append(
            FailedTaskRecord(
                task=task,
                round_id=self.round_id if round_id is None else round_id,
                stage=stage,
                error_message=error_message,
            )
        )

    def record_failed_tasks(
        self,
        tasks: list[FactorTask],
        *,
        round_id: int | None = None,
        stage: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """Append multiple failed tasks from the same workflow stage."""

        for task in tasks:
            self.record_failed_task(
                task,
                round_id=round_id,
                stage=stage,
                error_message=error_message,
            )
