"""Minimal AlphaAgent loop implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from alphaagent_qdatasdk.app.conf import AlphaAgentLoopConfig
from alphaagent_qdatasdk.core import (
    AlphaAgentHypothesis,
    ExperimentResult,
    FactorExperiment,
    HypothesisFeedback,
    Trace,
)
from alphaagent_qdatasdk.workflow.factory import (
    AlphaAgentWorkflowComponents,
    build_workflow_components,
)
from alphaagent_qdatasdk.workflow.round_output import LoopRoundOutput


@dataclass(slots=True)
class AlphaAgentLoop:
    """Six-stage alpha-research workflow."""

    config: AlphaAgentLoopConfig
    trace: Trace = field(init=False)
    components: AlphaAgentWorkflowComponents = field(init=False)

    def __post_init__(self) -> None:
        self.trace = Trace(
            active_direction=self.config.active_direction,
            scenario=self.config.scenario,
        )
        self.components = build_workflow_components(self.config)

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
        prev_out: dict[str, object] = {}

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
        """Generate one hypothesis through the configured stage implementation."""

        return self.components.hypothesis_generator.hypothesis_generation(self.trace, round_id)

    def experiment_generation(
        self,
        hypothesis: AlphaAgentHypothesis,
        round_id: int,
    ) -> FactorExperiment:
        """Convert a hypothesis into factor tasks."""

        return self.components.experiment_stage.generate(hypothesis, self.trace, round_id)

    def coder(self, experiment: FactorExperiment, round_id: int) -> list[Path]:
        """Materialize task workspaces for the current round."""

        return self.components.coder_stage.materialize(experiment, round_id)

    def runner(
        self,
        experiment: FactorExperiment,
        sub_workspace_list: list[Path],
        round_id: int,
    ) -> ExperimentResult:
        """Run the current experiment."""

        return self.components.runner_stage.run(experiment, sub_workspace_list, round_id)

    def feedback(
        self,
        hypothesis: AlphaAgentHypothesis,
        experiment: FactorExperiment,
        result: ExperimentResult,
        round_id: int,
    ) -> HypothesisFeedback:
        """Produce structured round feedback."""

        return self.components.feedback_stage.generate(
            hypothesis,
            experiment,
            result,
            self.trace,
            round_id,
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

        self.components.trace_stage.update(
            self.trace,
            hypothesis,
            experiment,
            result,
            feedback,
            round_id,
        )
