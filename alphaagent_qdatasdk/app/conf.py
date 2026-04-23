"""Configuration for the AlphaAgent_qdatasdk application."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from alphaagent_qdatasdk.core.types import JsonDict


@dataclass(slots=True)
class AlphaAgentLoopConfig:
    """Minimal configuration needed to construct an AlphaAgent loop."""

    active_direction: str = "momentum factor"
    scenario: JsonDict = field(
        default_factory=lambda: {
            "market": "A-share",
            "data_source": "qdatasdk",
            "frequency": "daily",
        }
    )
    max_rounds: int = 1
    workspace: Path = Path("workspace")
    dry_run: bool = True


DEFAULT_LOOP_CONFIG = AlphaAgentLoopConfig()


def build_loop_config(
    *,
    active_direction: str | None = None,
    max_rounds: int | None = None,
    workspace: str | Path | None = None,
    dry_run: bool | None = None,
) -> AlphaAgentLoopConfig:
    """Build a loop config from CLI-friendly optional values."""

    config = AlphaAgentLoopConfig()
    if active_direction is not None:
        config.active_direction = active_direction
    if max_rounds is not None:
        config.max_rounds = max_rounds
    if workspace is not None:
        config.workspace = Path(workspace)
    if dry_run is not None:
        config.dry_run = dry_run
    return config
