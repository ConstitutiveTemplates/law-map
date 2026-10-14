"""Split a section file into its YAML front matter and Markdown body."""

from __future__ import annotations

from pathlib import Path

import yaml

from .const import FRONT_MATTER_RE


def split_front_matter(text: str) -> tuple[dict | None, str]:
    """``(front matter mapping, body)``; ``(None, text)`` when there is none.

    Raises ``yaml.YAMLError`` when the block is present but not valid YAML.
    """
    match = FRONT_MATTER_RE.match(text)
    if match is None:
        return None, text
    data = yaml.safe_load(match.group(1))
    if not isinstance(data, dict):
        return None, text[match.end():]
    return data, text[match.end():]


def read_section(path: Path) -> tuple[dict | None, str]:
    return split_front_matter(path.read_text(encoding="utf-8"))
