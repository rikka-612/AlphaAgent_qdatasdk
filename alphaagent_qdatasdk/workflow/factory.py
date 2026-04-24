"""Workflow wiring for AlphaAgent_qdatasdk."""

from __future__ import annotations

from dataclasses import dataclass

from alphaagent_qdatasdk.app.conf import AlphaAgentLoopConfig
from alphaagent_qdatasdk.core import AlphaAgentHypothesisGen
from alphaagent_qdatasdk.llm import LLMClient
from alphaagent_qdatasdk.qdatasdk import QDataSDKHypothesisGen
from alphaagent_qdatasdk.workflow.coder_stage import FactorCoderStage
from alphaagent_qdatasdk.workflow.experiment_stage import FactorExperimentStage
from alphaagent_qdatasdk.workflow.feedback_stage import FactorFeedbackStage
from alphaagent_qdatasdk.workflow.runner_stage import FactorRunnerStage
from alphaagent_qdatasdk.workflow.trace_stage import TraceStage


@dataclass(slots=True)
class AlphaAgentWorkflowComponents:
    """Concrete components used by one workflow loop."""

    llm_client: LLMClient | None
    hypothesis_generator: AlphaAgentHypothesisGen
    experiment_stage: FactorExperimentStage
    coder_stage: FactorCoderStage
    runner_stage: FactorRunnerStage
    feedback_stage: FactorFeedbackStage
    trace_stage: TraceStage


def build_workflow_components(config: AlphaAgentLoopConfig) -> AlphaAgentWorkflowComponents:
    """Build the concrete components for the configured workflow."""

    llm_client: LLMClient | None = None
    if not config.dry_run:
        if config.llm is None:
            raise ValueError("LLM config is required when dry_run=False.")
        llm_client = LLMClient(config.llm)

    return AlphaAgentWorkflowComponents(
        llm_client=llm_client,
        hypothesis_generator=QDataSDKHypothesisGen(config, llm_client),
        experiment_stage=FactorExperimentStage(config, llm_client),
        coder_stage=FactorCoderStage(config),
        runner_stage=FactorRunnerStage(config),
        feedback_stage=FactorFeedbackStage(config, llm_client),
        trace_stage=TraceStage(),
    )
