"""Experiment-generation stage implementation."""

from __future__ import annotations

from dataclasses import dataclass

from alphaagent_qdatasdk.app.conf import AlphaAgentLoopConfig
from alphaagent_qdatasdk.core import AlphaAgentHypothesis, FactorExperiment, FactorTask, Trace
from alphaagent_qdatasdk.llm import LLMClient
from alphaagent_qdatasdk.prompts import (
    EXPERIMENT_SYSTEM_PROMPT,
    build_experiment_user_prompt,
)
from alphaagent_qdatasdk.workflow.common import (
    as_string_list,
    has_required_strings,
    payload_to_text,
    summarize_text,
    trace_summary,
)


@dataclass(slots=True)
class FactorExperimentStage:
    """Build a structured experiment package from a hypothesis."""

    config: AlphaAgentLoopConfig
    llm_client: LLMClient | None = None

    def generate(
        self,
        hypothesis: AlphaAgentHypothesis,
        trace: Trace,
        round_id: int,
    ) -> FactorExperiment:
        if not self.config.dry_run and self.llm_client is not None:
            payload = self.llm_client.chat_json(
                system_prompt=EXPERIMENT_SYSTEM_PROMPT,
                user_prompt=build_experiment_user_prompt(
                    hypothesis=hypothesis.hypothesis,
                    scenario=self.config.scenario,
                    trace_summary=trace_summary(trace),
                ),
                max_tokens=180,
            )
            if "_raw_text" in payload:
                return self._fallback_from_text(
                    hypothesis=hypothesis,
                    raw_text=str(payload["_raw_text"]),
                    round_id=round_id,
                )
            if not has_required_strings(
                payload,
                ["factor_name", "expression_text", "notes"],
            ) or not isinstance(payload.get("required_fields"), list):
                return self._fallback_from_text(
                    hypothesis=hypothesis,
                    raw_text=payload_to_text(payload),
                    round_id=round_id,
                )
            task = FactorTask(
                task_id=f"round-{round_id}-task-1",
                factor_name=str(payload.get("factor_name", "llm_factor")).strip(),
                expression_text=str(payload.get("expression_text", "")).strip(),
                required_fields=as_string_list(payload.get("required_fields")),
                notes=str(payload.get("notes", "")).strip(),
            )
            return self._build_experiment(hypothesis, task, round_id)

        task = FactorTask(
            task_id=f"round-{round_id}-task-1",
            factor_name="mock_volume_corrected_momentum",
            expression_text="rank(close / delay(close, 20)) * rank(volume / shares_float)",
            required_fields=["close", "volume", "shares_float"],
            notes="Dry-run task; expression is not executed yet.",
        )
        return self._build_experiment(hypothesis, task, round_id)

    def _fallback_from_text(
        self,
        *,
        hypothesis: AlphaAgentHypothesis,
        raw_text: str,
        round_id: int,
    ) -> FactorExperiment:
        task = FactorTask(
            task_id=f"round-{round_id}-task-1",
            factor_name=f"llm_candidate_round_{round_id}",
            expression_text="TODO_FROM_LLM_TEXT",
            required_fields=[],
            notes=summarize_text(raw_text, 300),
        )
        experiment = self._build_experiment(hypothesis, task, round_id)
        experiment.run_config["llm_fallback"] = True
        return experiment

    def _build_experiment(
        self,
        hypothesis: AlphaAgentHypothesis,
        task: FactorTask,
        round_id: int,
    ) -> FactorExperiment:
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
