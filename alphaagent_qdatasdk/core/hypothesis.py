"""Hypothesis contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from alphaagent_qdatasdk.core.trace import Trace


@dataclass(slots=True)
class AlphaAgentHypothesis:
    """Research hypothesis proposed by the hypothesis generation stage."""

    hypothesis: str
    reason: str
    concise_reason: str
    concise_observation: str
    concise_justification: str
    concise_knowledge: str


class AlphaAgentHypothesisGen(ABC):
    """Interface for scenario-specific hypothesis generation."""

    @abstractmethod
    def hypothesis_generation(self, trace: Trace, round_id: int) -> AlphaAgentHypothesis:
        """Generate one researchable hypothesis from the current trace."""
