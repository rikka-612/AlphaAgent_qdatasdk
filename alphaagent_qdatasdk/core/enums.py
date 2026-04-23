"""Enum contracts shared by workflow stages."""

from __future__ import annotations

from enum import Enum


class FeedbackDecision(str, Enum):
    """Control-flow decision produced by the feedback stage."""

    CONTINUE = "continue"
    REFINE = "refine"
    BRANCH = "branch"
    STOP = "stop"


class ExperimentStatus(str, Enum):
    """Execution status produced by the runner stage."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
