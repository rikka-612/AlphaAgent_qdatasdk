"""Lightweight YAML prompt loader for repo-managed prompt files."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml


PROMPTS_DIR = Path(__file__).resolve().parent


@lru_cache(maxsize=None)
def load_prompt_yaml(name: str) -> dict[str, str]:
    prompt_path = PROMPTS_DIR / f"{name}.yaml"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt YAML not found: {prompt_path}")
    data = yaml.safe_load(prompt_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Prompt YAML must be a mapping: {prompt_path}")
    return {str(key): str(value) for key, value in data.items()}
