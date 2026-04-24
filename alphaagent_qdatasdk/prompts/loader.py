"""Lightweight YAML prompt loader for repo-managed prompt files."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path


PROMPTS_DIR = Path(__file__).resolve().parent


def _strip_block_lines(lines: list[str]) -> str:
    if not lines:
        return ""

    min_indent: int | None = None
    for line in lines:
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        min_indent = indent if min_indent is None else min(min_indent, indent)

    if min_indent is None:
        return ""

    normalized = [line[min_indent:] if len(line) >= min_indent else "" for line in lines]
    return "\n".join(normalized).rstrip()


def _parse_prompt_yaml(text: str) -> dict[str, str]:
    data: dict[str, str] = {}
    lines = text.splitlines()
    index = 0

    while index < len(lines):
        raw_line = lines[index]
        stripped = raw_line.strip()

        if not stripped or stripped.startswith("#"):
            index += 1
            continue

        if ":" not in raw_line:
            raise ValueError(f"Invalid YAML prompt line: {raw_line!r}")

        key, remainder = raw_line.split(":", 1)
        key = key.strip()
        remainder = remainder.strip()

        if not key:
            raise ValueError(f"Missing key in YAML prompt line: {raw_line!r}")

        if remainder in {"|", "|-", "|+"}:
            index += 1
            block_lines: list[str] = []
            while index < len(lines):
                candidate = lines[index]
                if candidate.startswith(" ") or candidate == "":
                    block_lines.append(candidate)
                    index += 1
                    continue
                break
            data[key] = _strip_block_lines(block_lines)
            continue

        if remainder.startswith(("'", '"')) and remainder.endswith(("'", '"')):
            remainder = remainder[1:-1]

        data[key] = remainder
        index += 1

    return data


@lru_cache(maxsize=None)
def load_prompt_yaml(name: str) -> dict[str, str]:
    prompt_path = PROMPTS_DIR / f"{name}.yaml"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt YAML not found: {prompt_path}")
    return _parse_prompt_yaml(prompt_path.read_text(encoding="utf-8"))
