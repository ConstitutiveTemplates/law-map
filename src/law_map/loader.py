"""Corpus discovery and loading.

Walks an obligations directory, parses each ``*.yml`` file (skipping
``_``-prefixed basenames such as ``_example.yml``), validates every
document via :mod:`law_map.validate`, and collects the results into a
:class:`~law_map.model.Corpus`. Never raises on bad content — problems
land in ``corpus.errors`` for callers to report.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from .model import PACKS, Corpus, Obligation, obligation_pack
from .validate import check_unique_ids, validate_obligation_document


def load_corpus(
    root: Path, today: date | None = None, packs: Iterable[str] | None = None
) -> Corpus:
    """Load every non-underscore obligation file under root (recursive).

    Returns a Corpus with per-file validation issues in ``errors``; never
    raises on bad content. ``root`` may be missing (empty corpus). ``today``
    pins the date for scheduled-effective warnings (defaults to today).
    ``packs`` selects which packs land in ``obligations`` (default: all);
    every file is still validated, and obligations from other packs go to
    ``excluded`` so cross-pack ``requires``/``conflicts`` keep resolving.
    """
    selected = set(PACKS if packs is None else packs)
    corpus = Corpus()
    root = Path(root)
    if not root.is_dir():
        return corpus
    for path in sorted(root.rglob("*.yml")):
        if path.name.startswith("_"):
            continue
        data = _load_document(path, corpus.errors)
        if data is None:
            continue
        validate_obligation_document(
            data, path=path, errors=corpus.errors, warnings=corpus.warnings, today=today
        )
        ob = Obligation(path=path, data=data)
        if obligation_pack(ob) in selected:
            corpus.obligations.append(ob)
        else:
            corpus.excluded.append(ob)
    check_unique_ids(corpus)
    return corpus


def _load_document(path: Path, errors: list[str]) -> dict[str, Any] | None:
    """Parse one YAML file as a mapping; ``None`` with an error appended."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"cannot read {path}: {exc}")
        return None
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        errors.append(f"invalid YAML in {path}: {exc}")
        return None
    if not isinstance(data, dict):
        errors.append(f"{path}: document must be a mapping, got {type(data).__name__}")
        return None
    return data
