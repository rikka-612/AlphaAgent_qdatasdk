"""Runner-stage implementation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from alphaagent_qdatasdk.app.conf import AlphaAgentLoopConfig
from alphaagent_qdatasdk.core import ExperimentResult, ExperimentStatus, FactorExperiment


@dataclass(slots=True)
class FactorRunnerStage:
    """Produce an experiment result from the prepared workspaces."""

    config: AlphaAgentLoopConfig

    def run(
        self,
        experiment: FactorExperiment,
        sub_workspace_list: list[Path],
        round_id: int,
    ) -> ExperimentResult:
        if experiment.run_config.get("llm_fallback"):
            return ExperimentResult(
                status=ExperimentStatus.FAILED,
                performance_summary={
                    "mode": "validation_failed",
                    "factor_count": len(experiment.factor_tasks),
                    "workspace_count": len(sub_workspace_list),
                },
                baseline_comparison={"available": False, "reason": "No baseline runner yet."},
                sota_comparison={"available": False, "reason": "No SOTA trace yet."},
                error_message="Experiment generation fell back from invalid or non-JSON LLM output.",
            )

        return ExperimentResult(
            status=ExperimentStatus.SUCCESS,
            artifact_paths={
                "combined_factors": str(
                    self.config.workspace / f"round_{round_id}" / "combined_factors_df.pkl"
                )
            },
            performance_summary={
                "mode": "dry_run",
                "factor_count": len(experiment.factor_tasks),
                "workspace_count": len(sub_workspace_list),
            },
            baseline_comparison={"available": False, "reason": "No baseline runner yet."},
            sota_comparison={"available": False, "reason": "No SOTA trace yet."},
        )
