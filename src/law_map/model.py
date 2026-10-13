"""Core types and vocabulary for the law-map obligation corpus.

This module owns the shared building blocks only: the ``Obligation`` /
``Corpus`` dataclasses, the controlled vocabularies (categories,
modalities, severities, ...), ISO date parsing, and read-only grounding
accessors.

Single-file validation lives in :mod:`law_map.validate` (obligations) and
:mod:`law_map.checkspecs` (check specs), corpus discovery
in :mod:`law_map.loader`, cross-file links in :mod:`law_map.refs`, and
codex linkage in :mod:`law_map.codex`.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

__all__ = [
    "CATEGORIES",
    "ENFORCEMENT_LEVELS",
    "IDENT_RE",
    "MODALITIES",
    "SEVERITIES",
    "SOURCE_TYPES",
    "STATUSES",
    "SUBDIVISION_JURISDICTIONS",
    "Corpus",
    "Obligation",
    "iter_groundings",
    "obligation_groundings",
    "parse_iso_date",
]

IDENT_RE = re.compile(r"^obligation\.([a-z0-9]+(-[a-z0-9]+)*)\.([a-z0-9]+(-[a-z0-9]+)*)$")

CATEGORIES = {"privacy", "security", "copyright", "ai", "licensing", "telemetry", "crypto"}
MODALITIES = {"obligation", "prohibition", "permission"}
SEVERITIES = {"info", "advisory", "high", "critical"}
SOURCE_TYPES = {"statute", "regulation", "precedent", "guidance", "standard", "model_code"}
STATUSES = {"in_force", "scheduled", "proposed", "superseded"}
ENFORCEMENT_LEVELS = {"L0", "L1", "L2"}
SUBDIVISION_JURISDICTIONS = {"US", "CA", "AU", "DE", "GB"}


@dataclass
class Obligation:
    """A single parsed obligation document."""

    path: Path
    data: dict[str, Any]

    @property
    def id(self) -> str:
        return str(self.data.get("id", ""))


@dataclass
class Corpus:
    """Loaded obligation files plus the collected validation issues."""

    obligations: list[Obligation] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def ok(self) -> bool:
        return not self.errors


def parse_iso_date(value: object) -> date | None:
    """Parse an ISO ``YYYY-MM-DD`` date string; ``None`` when not a valid date."""
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def obligation_groundings(ob: Obligation) -> list[dict[str, Any]]:
    """The mapping groundings of one obligation (malformed entries skipped)."""
    return [g for g in ob.data.get("groundings", []) if isinstance(g, dict)]


def iter_groundings(corpus: Corpus) -> Iterator[dict[str, Any]]:
    """Every mapping grounding in the corpus, in obligation order."""
    for ob in corpus.obligations:
        yield from obligation_groundings(ob)


_COMPAT_EXPORTS: dict[str, str] = {
    "load_corpus": "law_map.loader",
    "check_unique_ids": "law_map.validate",
    "validate_obligation_document": "law_map.validate",
    "check_cross_references": "law_map.refs",
    "CODEX_SECTIONS_DIR": "law_map.codex",
    "codex_section_path": "law_map.codex",
    "check_codex_sections": "law_map.codex",
    "check_codex_coverage": "law_map.codex",
    "unresolved_section_error": "law_map.codex",
}


def __getattr__(name: str) -> object:
    """Backward-compatible facade for the pre-split ``model`` surface.

    Canonical homes are :mod:`law_map.loader` (``load_corpus``),
    :mod:`law_map.validate` (single-file checks), :mod:`law_map.refs`
    (cross-file checks), and :mod:`law_map.codex` (codex linkage).
    Lazy import keeps the ``model -> validate -> model`` cycle unobservable.
    """
    if name in _COMPAT_EXPORTS:
        import importlib

        return getattr(importlib.import_module(_COMPAT_EXPORTS[name]), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
