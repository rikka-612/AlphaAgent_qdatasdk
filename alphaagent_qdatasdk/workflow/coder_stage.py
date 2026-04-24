"""Coder-stage implementation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from alphaagent_qdatasdk.app.conf import AlphaAgentLoopConfig
from alphaagent_qdatasdk.core import FactorExperiment


@dataclass(slots=True)
class FactorCoderStage:
    """Materialize per-task workspaces."""

    config: AlphaAgentLoopConfig

    def materialize(self, experiment: FactorExperiment, round_id: int) -> list[Path]:
        workspaces: list[Path] = []
        for task in experiment.factor_tasks:
            workspace = self.config.workspace / f"round_{round_id}" / task.task_id
            workspaces.append(workspace)
        return workspaces
