"""qdatasdk-specific hypothesis generation."""

from __future__ import annotations

from alphaagent_qdatasdk.app.conf import AlphaAgentLoopConfig
from alphaagent_qdatasdk.core import AlphaAgentHypothesis, AlphaAgentHypothesisGen, Trace
from alphaagent_qdatasdk.llm import LLMClient
from alphaagent_qdatasdk.prompts import HYPOTHESIS_SYSTEM_PROMPT, build_hypothesis_user_prompt


class QDataSDKHypothesisGen(AlphaAgentHypothesisGen):
    """Generate hypotheses for the qdatasdk alpha-research scenario."""

    def __init__(self, config: AlphaAgentLoopConfig, llm_client: LLMClient | None = None) -> None:
        self.config = config
        self.llm_client = llm_client

    def hypothesis_generation(self, trace: Trace, round_id: int) -> AlphaAgentHypothesis:
        if not self.config.dry_run and self.llm_client is not None:
            payload = self.llm_client.chat_json(
                system_prompt=HYPOTHESIS_SYSTEM_PROMPT,
                user_prompt=build_hypothesis_user_prompt(
                    active_direction=trace.active_direction,
                    scenario=self.config.scenario,
                    trace_summary=self._trace_summary(trace),
                ),
                max_tokens=220,
            )
            if "_raw_text" in payload:
                return self._fallback_hypothesis_from_text(
                    trace,
                    str(payload["_raw_text"]),
                    round_id,
                )
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
                return self._fallback_hypothesis_from_text(trace, str(payload), round_id)
            return AlphaAgentHypothesis(
                hypothesis=str(payload.get("hypothesis", "")).strip(),
                reason=str(payload.get("reason", "")).strip(),
                concise_reason=str(payload.get("concise_reason", "")).strip(),
                concise_observation=str(payload.get("concise_observation", "")).strip(),
                concise_justification=str(payload.get("concise_justification", "")).strip(),
                concise_knowledge=str(payload.get("concise_knowledge", "")).strip(),
            )

        direction = trace.active_direction
        market = self.config.scenario.get("market", "unknown market")
        return AlphaAgentHypothesis(
            hypothesis=f"{direction} may improve cross-sectional ranking in {market}.",
            reason="This dry-run hypothesis checks whether the workflow contract is wired.",
            concise_reason="Validate workflow wiring before real LLM generation.",
            concise_observation="The repository currently has qdatasdk examples but no live factor loop.",
            concise_justification="A deterministic mock round makes later stage replacement safer.",
            concise_knowledge=f"Round {round_id} uses qdatasdk as the intended data source.",
        )

    def _fallback_hypothesis_from_text(
        self,
        trace: Trace,
        raw_text: str,
        round_id: int,
    ) -> AlphaAgentHypothesis:
        summary = self._summarize_text(raw_text, 280)
        return AlphaAgentHypothesis(
            hypothesis=summary or f"{trace.active_direction} remains a candidate alpha direction.",
            reason="LLM returned non-JSON output; using textual fallback.",
            concise_reason="Converted Kimi reasoning output into a usable hypothesis draft.",
            concise_observation=self._summarize_text(raw_text, 160),
            concise_justification="The Kimi coding endpoint may return reasoning-style content instead of strict JSON.",
            concise_knowledge=f"Round {round_id} used the provider-compatible fallback parser.",
        )

    @staticmethod
    def _trace_summary(trace: Trace) -> str:
        latest = trace.latest_round()
        if latest is None:
            return "No previous rounds."
        return (
            f"Latest round={latest.round_id}; "
            f"decision={latest.feedback.decision.value}; "
            f"status={latest.result.status.value}; "
            f"hypothesis={latest.hypothesis.hypothesis}"
        )

    @staticmethod
    def _has_required_strings(payload: dict[str, object], keys: list[str]) -> bool:
        return all(str(payload.get(key, "")).strip() for key in keys)

    @staticmethod
    def _summarize_text(text: str, limit: int) -> str:
        compact = " ".join(text.split())
        if len(compact) <= limit:
            return compact
        return compact[: limit - 3] + "..."
