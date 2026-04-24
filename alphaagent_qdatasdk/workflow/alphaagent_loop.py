"""Minimal AlphaAgent loop implementation.

This module wires the six-stage contract from ``Agents.md`` with deterministic
mock behavior. The goal is to make the loop runnable before plugging in LLM,
qdatasdk, coder, and runner integrations.
"""

from __future__ import annotations

import json
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
from alphaagent_qdatasdk.llm import LLMClient
from alphaagent_qdatasdk.prompts import (
    EXPERIMENT_SYSTEM_PROMPT,
    FEEDBACK_SYSTEM_PROMPT,
    HYPOTHESIS_SYSTEM_PROMPT,
    build_experiment_user_prompt,
    build_feedback_user_prompt,
    build_hypothesis_user_prompt,
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
    llm_client: LLMClient | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        self.trace = Trace(
            active_direction=self.config.active_direction,
            scenario=self.config.scenario,
        )
        if not self.config.dry_run:
            if self.config.llm is None:
                raise ValueError("LLM config is required when dry_run=False.")
            self.llm_client = LLMClient(self.config.llm)

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

        if not self.config.dry_run and self.llm_client is not None:
            payload = self.llm_client.chat_json(
                system_prompt=HYPOTHESIS_SYSTEM_PROMPT,
                user_prompt=build_hypothesis_user_prompt(
                    active_direction=self.trace.active_direction,
                    scenario=self.config.scenario,
                    trace_summary=self._trace_summary(),
                ),
                max_tokens=220,
            )
            if "_raw_text" in payload:
                return self._fallback_hypothesis_from_text(str(payload["_raw_text"]), round_id)
            if not self._has_required_strings(
                payload,
                [
                    "hypothesis",
                    "reason",
                    "concise_reason",
                    "concise_observation",
                    "concise_justification",
                    "concise_knowledge",
                ],
            ):
                return self._fallback_hypothesis_from_text(self._payload_to_text(payload), round_id)
            return AlphaAgentHypothesis(
                hypothesis=str(payload.get("hypothesis", "")).strip(),
                reason=str(payload.get("reason", "")).strip(),
                concise_reason=str(payload.get("concise_reason", "")).strip(),
                concise_observation=str(payload.get("concise_observation", "")).strip(),
                concise_justification=str(payload.get("concise_justification", "")).strip(),
                concise_knowledge=str(payload.get("concise_knowledge", "")).strip(),
            )

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

        if not self.config.dry_run and self.llm_client is not None:
            payload = self.llm_client.chat_json(
                system_prompt=EXPERIMENT_SYSTEM_PROMPT,
                user_prompt=build_experiment_user_prompt(
                    hypothesis=hypothesis.hypothesis,
                    scenario=self.config.scenario,
                    trace_summary=self._trace_summary(),
                ),
                max_tokens=180,
            )
            if "_raw_text" in payload:
                return self._fallback_experiment_from_text(
                    hypothesis=hypothesis,
                    raw_text=str(payload["_raw_text"]),
                    round_id=round_id,
                )
            if not self._has_required_strings(
                payload,
                ["factor_name", "expression_text", "notes"],
            ) or not isinstance(payload.get("required_fields"), list):
                return self._fallback_experiment_from_text(
                    hypothesis=hypothesis,
                    raw_text=self._payload_to_text(payload),
                    round_id=round_id,
                )
            task = FactorTask(
                task_id=f"round-{round_id}-task-1",
                factor_name=str(payload.get("factor_name", "llm_factor")).strip(),
                expression_text=str(payload.get("expression_text", "")).strip(),
                required_fields=self._as_string_list(payload.get("required_fields")),
                notes=str(payload.get("notes", "")).strip(),
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

    def feedback(
        self,
        hypothesis: AlphaAgentHypothesis,
        experiment: FactorExperiment,
        result: ExperimentResult,
        round_id: int,
    ) -> HypothesisFeedback:
        """Produce deterministic feedback for the mock round."""

        if not self.config.dry_run and self.llm_client is not None:
            payload = self.llm_client.chat_json(
                system_prompt=FEEDBACK_SYSTEM_PROMPT,
                user_prompt=build_feedback_user_prompt(
                    hypothesis=hypothesis.hypothesis,
                    performance_summary=result.performance_summary,
                    sota_comparison=result.sota_comparison,
                    trace_summary=self._trace_summary(),
                ),
                max_tokens=220,
            )
            if "_raw_text" in payload:
                return self._fallback_feedback_from_text(
                    hypothesis=hypothesis,
                    experiment=experiment,
                    result=result,
                    raw_text=str(payload["_raw_text"]),
                    round_id=round_id,
                )
            if not self._has_required_strings(
                payload,
                ["observations", "hypothesis_evaluation", "decision", "reason"],
            ) or not self._is_feedback_decision(payload.get("decision")):
                return self._fallback_feedback_from_text(
                    hypothesis=hypothesis,
                    experiment=experiment,
                    result=result,
                    raw_text=self._payload_to_text(payload),
                    round_id=round_id,
                )
            return HypothesisFeedback(
                observations=str(payload.get("observations", "")).strip(),
                hypothesis_evaluation=str(payload.get("hypothesis_evaluation", "")).strip(),
                decision=self._parse_feedback_decision(payload.get("decision")),
                reason=str(payload.get("reason", "")).strip(),
                strengths=self._as_string_list(payload.get("strengths")),
                weaknesses=self._as_string_list(payload.get("weaknesses")),
                next_direction=self._optional_string(payload.get("next_direction")),
                new_hypothesis=self._optional_string(payload.get("new_hypothesis")),
                quality_score=self._build_quality_score(payload.get("quality_score")),
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

    def _fallback_hypothesis_from_text(self, raw_text: str, round_id: int) -> AlphaAgentHypothesis:
        """Build a usable hypothesis object from non-JSON LLM output."""

        summary = self._summarize_text(raw_text, 280)
        return AlphaAgentHypothesis(
            hypothesis=summary or f"{self.trace.active_direction} remains a candidate alpha direction.",
            reason="LLM returned non-JSON output; using textual fallback.",
            concise_reason="Converted Kimi reasoning output into a usable hypothesis draft.",
            concise_observation=self._summarize_text(raw_text, 160),
            concise_justification="The Kimi coding endpoint may return reasoning-style content instead of strict JSON.",
            concise_knowledge=f"Round {round_id} used the provider-compatible fallback parser.",
        )

    def _fallback_experiment_from_text(
        self,
        *,
        hypothesis: AlphaAgentHypothesis,
        raw_text: str,
        round_id: int,
    ) -> FactorExperiment:
        """Build a usable experiment object from non-JSON LLM output."""

        task = FactorTask(
            task_id=f"round-{round_id}-task-1",
            factor_name=f"llm_candidate_round_{round_id}",
            expression_text="TODO_FROM_LLM_TEXT",
            required_fields=[],
            notes=self._summarize_text(raw_text, 300),
        )
        return FactorExperiment(
            experiment_id=f"round-{round_id}-experiment",
            hypothesis=hypothesis,
            factor_tasks=[task],
            data_requirements={"source": "qdatasdk"},
            run_config={
                "dry_run": self.config.dry_run,
                "workspace": str(self.config.workspace),
                "llm_fallback": True,
            },
            output_schema={
                "factor_artifact": "combined_factors_df.pkl",
                "result": "ExperimentResult",
            },
        )

    def _fallback_feedback_from_text(
        self,
        *,
        hypothesis: AlphaAgentHypothesis,
        experiment: FactorExperiment,
        result: ExperimentResult,
        raw_text: str,
        round_id: int,
    ) -> HypothesisFeedback:
        """Build a usable feedback object from non-JSON LLM output."""

        decision = FeedbackDecision.CONTINUE if result.succeeded else FeedbackDecision.REFINE
        return HypothesisFeedback(
            observations=f"Round {round_id} used LLM textual fallback for feedback.",
            hypothesis_evaluation=self._summarize_text(raw_text, 280),
            decision=decision,
            reason="Kimi returned non-JSON output; using structured fallback while preserving the call path.",
            strengths=[hypothesis.concise_reason],
            weaknesses=["Feedback JSON was unavailable; see quality_score.details.llm_raw_text."],
            next_direction=self.trace.active_direction,
            new_hypothesis=None,
            quality_score=FactorQualityScore(
                scorer_name="llm-feedback-fallback",
                score_version="draft",
                rationale="Stored raw LLM feedback text because strict JSON was unavailable.",
                details={
                    "llm_raw_text": self._summarize_text(raw_text, 600),
                    "factor_count": len(experiment.factor_tasks),
                    "result_status": result.status.value,
                },
            ),
        )

    def _trace_summary(self) -> str:
        latest = self.trace.latest_round()
        if latest is None:
            return "No previous rounds."
        return (
            f"Latest round={latest.round_id}; "
            f"decision={latest.feedback.decision.value}; "
            f"status={latest.result.status.value}; "
            f"hypothesis={latest.hypothesis.hypothesis}"
        )

    @staticmethod
    def _as_string_list(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return [str(value).strip()] if str(value).strip() else []

    @staticmethod
    def _optional_string(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _parse_feedback_decision(value: Any) -> FeedbackDecision:
        try:
            return FeedbackDecision(str(value).strip().lower())
        except ValueError:
            return FeedbackDecision.REFINE

    @staticmethod
    def _is_feedback_decision(value: Any) -> bool:
        try:
            FeedbackDecision(str(value).strip().lower())
        except ValueError:
            return False
        return True

    @staticmethod
    def _build_quality_score(value: Any) -> FactorQualityScore | None:
        if value is None:
            return None
        if not isinstance(value, dict):
            return FactorQualityScore(
                scorer_name="llm-feedback",
                score_version="draft",
                rationale="LLM returned a non-dict quality score payload.",
                details={"raw_quality_score": value},
            )
        raw_score = value.get("overall_score")
        try:
            overall_score = None if raw_score is None else float(raw_score)
        except (TypeError, ValueError):
            overall_score = None
        details = value.get("details")
        return FactorQualityScore(
            overall_score=overall_score,
            score_scale=str(value.get("score_scale", "unplanned")),
            scorer_name=str(value.get("scorer_name", "llm-feedback")),
            score_version=str(value.get("score_version", "draft")),
            rationale=str(value.get("rationale", "")).strip(),
            details=details if isinstance(details, dict) else {"raw_details": details},
        )

    @staticmethod
    def _summarize_text(text: str, limit: int) -> str:
        compact = " ".join(text.split())
        if len(compact) <= limit:
            return compact
        return compact[: limit - 3] + "..."

    @staticmethod
    def _has_required_strings(payload: dict[str, Any], keys: list[str]) -> bool:
        return all(str(payload.get(key, "")).strip() for key in keys)

    @staticmethod
    def _payload_to_text(payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False)
