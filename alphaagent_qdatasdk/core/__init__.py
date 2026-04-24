"""Core data contracts for the AlphaAgent_qdatasdk loop."""

from alphaagent_qdatasdk.core.enums import ExperimentStatus, FeedbackDecision
from alphaagent_qdatasdk.core.factor import FactorExperiment, FactorTask
from alphaagent_qdatasdk.core.feedback import FactorQualityScore, HypothesisFeedback
from alphaagent_qdatasdk.core.hypothesis import AlphaAgentHypothesis, AlphaAgentHypothesisGen
from alphaagent_qdatasdk.core.result import ExperimentResult
from alphaagent_qdatasdk.core.trace import FailedTaskRecord, RoundRecord, Trace
from alphaagent_qdatasdk.core.types import JsonDict

__all__ = [
    "AlphaAgentHypothesis",
    "AlphaAgentHypothesisGen",
    "ExperimentResult",
    "ExperimentStatus",
    "FailedTaskRecord",
    "FactorExperiment",
    "FactorTask",
    "FactorQualityScore",
    "FeedbackDecision",
    "HypothesisFeedback",
    "JsonDict",
    "RoundRecord",
    "Trace",
]
