"""Factor task and experiment contracts."""

from __future__ import annotations

from dataclasses import dataclass, field

from alphaagent_qdatasdk.core.hypothesis import AlphaAgentHypothesis
from alphaagent_qdatasdk.core.types import JsonDict


@dataclass(slots=True)
class FactorTask:
    """Smallest structured unit that the coder should implement."""

    task_id: str
    factor_name: str
    expression_text: str
    required_fields: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass(slots=True)
class FactorExperiment:
    """Structured experiment package for one research round.

    This is a data contract, not the executor. The runner owns execution.
    """

    experiment_id: str
    hypothesis: AlphaAgentHypothesis
    factor_tasks: list[FactorTask] = field(default_factory=list)
    data_requirements: JsonDict = field(default_factory=dict)
    run_config: JsonDict = field(default_factory=dict)
    output_schema: JsonDict = field(default_factory=dict)
