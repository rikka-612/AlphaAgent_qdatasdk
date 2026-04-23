"""Minimal AlphaAgent loop implementation.

This module wires the six-stage contract from ``Agents.md`` with deterministic
mock behavior. The goal is to make the loop runnable before plugging in LLM,
qdatasdk, coder, and runner integrations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from alphaagent_qdatasdk.app.conf import AlphaAgentLoopConfig
from alphaagent_qdatasdk.core import (
    AlphaAgentHypothesis,
    ExperimentResult,
    ExperimentStatus,
    FactorExperiment,
    FactorTask,
    FactorQualityScore,
    FeedbackDecision,
    HypothesisFeedback,
    RoundRecord,
    Trace,
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


@dataclass(slots=True)
class AlphaAgentLoop:
    """Six-stage alpha-research workflow."""

    config: AlphaAgentLoopConfig
    trace: Trace = field(init=False)

    def __post_init__(self) -> None:
        self.trace = Trace(
            active_direction=self.config.active_direction,
            scenario=self.config.scenario,
        )

    def run(self, max_rounds: int | None = None) -> list[LoopRoundOutput]:
        """Run the loop for a finite number of rounds."""

        rounds = self.config.max_rounds if max_rounds is None else max_rounds
        outputs: list[LoopRoundOutput] = []
        for _ in range(rounds):
            outputs.append(self.run_round())
        return outputs

    def run_round(self) -> LoopRoundOutput:
        """Run one complete hypothesis-to-trace round."""

        round_id = self.trace.round_id + 1
        prev_out: dict[str, Any] = {}

        prev_out["hypothesis"] = self.hypothesis_generation(round_id)
        prev_out["experiment"] = self.experiment_generation(prev_out["hypothesis"], round_id)
        prev_out["sub_workspace_list"] = self.coder(prev_out["experiment"], round_id)
        prev_out["result"] = self.runner(
            prev_out["experiment"],
            prev_out["sub_workspace_list"],
            round_id,
        )
        prev_out["feedback"] = self.feedback(
            prev_out["hypothesis"],
            prev_out["experiment"],
            prev_out["result"],
            round_id,
        )
        self.trace_update(
            prev_out["hypothesis"],
            prev_out["experiment"],
            prev_out["result"],
            prev_out["feedback"],
            round_id,
        )

        return LoopRoundOutput(
            round_id=round_id,
            hypothesis=prev_out["hypothesis"],
            experiment=prev_out["experiment"],
            sub_workspace_list=prev_out["sub_workspace_list"],
            result=prev_out["result"],
            feedback=prev_out["feedback"],
        )

    def hypothesis_generation(self, round_id: int) -> AlphaAgentHypothesis:
        """Generate a mock hypothesis from direction and scenario."""

        direction = self.trace.active_direction
        market = self.config.scenario.get("market", "unknown market")
        return AlphaAgentHypothesis(
            hypothesis=f"{direction} may improve cross-sectional ranking in {market}.",
            reason="This dry-run hypothesis checks whether the workflow contract is wired.",
            concise_reason="Validate workflow wiring before real LLM generation.",
            concise_observation="The repository currently has qdatasdk examples but no live factor loop.",
            concise_justification="A deterministic mock round makes later stage replacement safer.",
            concise_knowledge=f"Round {round_id} uses qdatasdk as the intended data source.",
        )

    def experiment_generation(
        self,
        hypothesis: AlphaAgentHypothesis,
        round_id: int,
    ) -> FactorExperiment:
        """Convert a mock hypothesis into factor tasks."""

        task = FactorTask(
            task_id=f"round-{round_id}-task-1",
            factor_name="mock_volume_corrected_momentum",
            expression_text="rank(close / delay(close, 20)) * rank(volume / shares_float)",
            required_fields=["close", "volume", "shares_float"],
            notes="Dry-run task; expression is not executed yet.",
        )
        return FactorExperiment(
            experiment_id=f"round-{round_id}-experiment",
            hypothesis=hypothesis,
            factor_tasks=[task],
            data_requirements={
                "fields": task.required_fields,
                "source": "qdatasdk",
            },
            run_config={
                "dry_run": self.config.dry_run,
                "workspace": str(self.config.workspace),
            },
            output_schema={
                "factor_artifact": "combined_factors_df.pkl",
                "result": "ExperimentResult",
            },
        )

    def coder(self, experiment: FactorExperiment, round_id: int) -> list[Path]:
        """Materialize task workspaces for the mock round."""

        workspaces: list[Path] = []
        for task in experiment.factor_tasks:
            workspace = self.config.workspace / f"round_{round_id}" / task.task_id
            workspaces.append(workspace)
        return workspaces

    def runner(
        self,
        experiment: FactorExperiment,
        sub_workspace_list: list[Path],
        round_id: int,
    ) -> ExperimentResult:
        """Return a deterministic dry-run result."""

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

    def feedback(
        self,
        hypothesis: AlphaAgentHypothesis,
        experiment: FactorExperiment,
        result: ExperimentResult,
        round_id: int,
    ) -> HypothesisFeedback:
        """Produce deterministic feedback for the mock round."""

        decision = FeedbackDecision.CONTINUE if result.succeeded else FeedbackDecision.REFINE
        return HypothesisFeedback(
            observations=f"Round {round_id} completed with {len(experiment.factor_tasks)} task(s).",
            hypothesis_evaluation=(
                "The hypothesis is structurally valid for the dry-run loop, "
                "but it has not been backtested."
            ),
            decision=decision,
            reason="Use the mock result to continue building the next integration layer.",
            strengths=[hypothesis.concise_reason],
            weaknesses=["No real qdatasdk query, code generation, or backtest has run yet."],
            next_direction=self.trace.active_direction,
            new_hypothesis=None,
            quality_score=FactorQualityScore(
                scorer_name="mock-feedback",
                score_version="draft",
                rationale="Quality scoring is only a placeholder until the scoring system is designed.",
                details={
                    "mode": "dry_run",
                    "factor_count": len(experiment.factor_tasks),
                    "has_real_backtest": False,
                },
            ),
        )

    def trace_update(
        self,
        hypothesis: AlphaAgentHypothesis,
        experiment: FactorExperiment,
        result: ExperimentResult,
        feedback: HypothesisFeedback,
        round_id: int,
    ) -> None:
        """Append the round record and update trace-level summary state."""

        record = RoundRecord(
            round_id=round_id,
            hypothesis=hypothesis,
            experiment=experiment,
            result=result,
            feedback=feedback,
        )
        self.trace.append_round(record)
        if result.succeeded and self.trace.current_sota is None:
            self.trace.set_current_sota(result)
