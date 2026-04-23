"""Experiment result contracts."""

from __future__ import annotations

from dataclasses import dataclass, field

from alphaagent_qdatasdk.core.enums import ExperimentStatus
from alphaagent_qdatasdk.core.types import JsonDict


@dataclass(slots=True)
class ExperimentResult:
    """Structured result emitted by the runner."""

    status: ExperimentStatus
    artifact_paths: dict[str, str] = field(default_factory=dict)
    performance_summary: JsonDict = field(default_factory=dict)
    baseline_comparison: JsonDict = field(default_factory=dict)
    sota_comparison: JsonDict = field(default_factory=dict)
    error_message: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.status == ExperimentStatus.SUCCESS
