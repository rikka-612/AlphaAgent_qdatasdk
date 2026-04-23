"""Compatibility exports for core data contracts.

Class definitions live in smaller category modules. Importing from this module
is still supported while the project is taking shape.
"""

from alphaagent_qdatasdk.core.enums import ExperimentStatus, FeedbackDecision
from alphaagent_qdatasdk.core.factor import FactorExperiment, FactorTask
from alphaagent_qdatasdk.core.feedback import FactorQualityScore, HypothesisFeedback
from alphaagent_qdatasdk.core.hypothesis import AlphaAgentHypothesis
from alphaagent_qdatasdk.core.result import ExperimentResult
from alphaagent_qdatasdk.core.trace import FailedTaskRecord, RoundRecord, Trace
from alphaagent_qdatasdk.core.types import JsonDict

__all__ = [
    "AlphaAgentHypothesis",
    "ExperimentResult",
    "ExperimentStatus",
    "FactorExperiment",
    "FactorTask",
    "FeedbackDecision",
    "FailedTaskRecord",
    "FactorQualityScore",
    "HypothesisFeedback",
    "JsonDict",
    "RoundRecord",
    "Trace",
]
