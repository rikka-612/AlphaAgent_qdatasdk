"""Feedback-stage implementation."""

from __future__ import annotations

from dataclasses import dataclass

from alphaagent_qdatasdk.app.conf import AlphaAgentLoopConfig
from alphaagent_qdatasdk.core import (
    AlphaAgentHypothesis,
    ExperimentResult,
    FactorExperiment,
    FactorQualityScore,
    FeedbackDecision,
    HypothesisFeedback,
    Trace,
)
from alphaagent_qdatasdk.llm import LLMClient
from alphaagent_qdatasdk.prompts import (
    FEEDBACK_SYSTEM_PROMPT,
    build_feedback_user_prompt,
)
from alphaagent_qdatasdk.workflow.common import (
    as_string_list,
    build_quality_score,
    has_required_strings,
    is_feedback_decision,
    optional_string,
    parse_feedback_decision,
    payload_to_text,
    summarize_text,
    trace_summary,
)


@dataclass(slots=True)
class FactorFeedbackStage:
    """Produce structured next-step feedback from experiment results."""

    config: AlphaAgentLoopConfig
    llm_client: LLMClient | None = None

    def generate(
        self,
        hypothesis: AlphaAgentHypothesis,
        experiment: FactorExperiment,
        result: ExperimentResult,
        trace: Trace,
        round_id: int,
    ) -> HypothesisFeedback:
        if not self.config.dry_run and self.llm_client is not None:
            payload = self.llm_client.chat_json(
                system_prompt=FEEDBACK_SYSTEM_PROMPT,
                user_prompt=build_feedback_user_prompt(
                    hypothesis=hypothesis.hypothesis,
                    performance_summary=result.performance_summary,
                    sota_comparison=result.sota_comparison,
                    trace_summary=trace_summary(trace),
                ),
                max_tokens=220,
            )
            if "_raw_text" in payload:
                return self._fallback_from_text(
                    hypothesis=hypothesis,
                    experiment=experiment,
                    result=result,
                    raw_text=str(payload["_raw_text"]),
                    trace=trace,
                    round_id=round_id,
                )
            if not has_required_strings(
                payload,
                ["observations", "hypothesis_evaluation", "decision", "reason"],
            ) or not is_feedback_decision(payload.get("decision")):
                return self._fallback_from_text(
                    hypothesis=hypothesis,
                    experiment=experiment,
                    result=result,
                    raw_text=payload_to_text(payload),
                    trace=trace,
                    round_id=round_id,
                )
            return HypothesisFeedback(
                observations=str(payload.get("observations", "")).strip(),
                hypothesis_evaluation=str(payload.get("hypothesis_evaluation", "")).strip(),
                decision=parse_feedback_decision(payload.get("decision")),
                reason=str(payload.get("reason", "")).strip(),
                strengths=as_string_list(payload.get("strengths")),
                weaknesses=as_string_list(payload.get("weaknesses")),
                next_direction=optional_string(payload.get("next_direction")),
                new_hypothesis=optional_string(payload.get("new_hypothesis")),
                quality_score=build_quality_score(payload.get("quality_score")),
            )

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
            next_direction=trace.active_direction,
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

    def _fallback_from_text(
        self,
        *,
        hypothesis: AlphaAgentHypothesis,
        experiment: FactorExperiment,
        result: ExperimentResult,
        raw_text: str,
        trace: Trace,
        round_id: int,
    ) -> HypothesisFeedback:
        decision = FeedbackDecision.CONTINUE if result.succeeded else FeedbackDecision.REFINE
        return HypothesisFeedback(
            observations=f"Round {round_id} used LLM textual fallback for feedback.",
            hypothesis_evaluation=summarize_text(raw_text, 280),
            decision=decision,
            reason="Kimi returned non-JSON output; using structured fallback while preserving the call path.",
            strengths=[hypothesis.concise_reason],
            weaknesses=["Feedback JSON was unavailable; see quality_score.details.llm_raw_text."],
            next_direction=trace.active_direction,
            new_hypothesis=None,
            quality_score=FactorQualityScore(
                scorer_name="llm-feedback-fallback",
                score_version="draft",
                rationale="Stored raw LLM feedback text because strict JSON was unavailable.",
                details={
                    "llm_raw_text": summarize_text(raw_text, 600),
                    "factor_count": len(experiment.factor_tasks),
                    "result_status": result.status.value,
                },
            ),
        )
