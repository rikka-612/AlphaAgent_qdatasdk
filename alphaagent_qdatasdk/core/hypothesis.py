"""Hypothesis contracts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AlphaAgentHypothesis:
    """Research hypothesis proposed by the hypothesis generation stage."""

    hypothesis: str
    reason: str
    concise_reason: str
    concise_observation: str
    concise_justification: str
    concise_knowledge: str
