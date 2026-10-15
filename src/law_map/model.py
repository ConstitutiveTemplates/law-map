"""Core types and vocabulary for the law-map obligation corpus.

This module owns the shared building blocks only: the ``Obligation`` /
``Corpus`` dataclasses, the controlled vocabularies (categories,
modalities, severities, ...), ISO date parsing, ISO 3166 jurisdiction /
subdivision checks (via pycountry), and read-only grounding accessors.

Single-file validation lives in :mod:`law_map.validate` (obligations) and
:mod:`law_map.checkspecs` (check specs), corpus discovery
in :mod:`law_map.loader`, cross-file links in :mod:`law_map.refs`, and
codex linkage in :mod:`law_map.kanon`.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import pycountry

__all__ = [
    "CATEGORIES",
    "CONFIDENCES",
    "ENFORCEMENT_LEVELS",
    "IDENT_RE",
    "JURISDICTION_ALIASES",
    "JURISDICTION_RE",
    "MODALITIES",
    "PACKS",
    "SCHEMA_VERSION",
    "SEVERITIES",
    "SOURCE_KINDS",
    "SOURCE_TYPE_PACK",
    "SOURCE_TYPES",
    "STATUSES",
    "STRENGTHS",
    "UNOFFICIAL_HOSTS",
    "Corpus",
    "Obligation",
    "grounding_review_status",
    "is_valid_jurisdiction",
    "is_valid_subdivision",
    "iter_groundings",
    "obligation_groundings",
    "obligation_pack",
    "obligation_review_status",
    "parse_iso_date",
]

IDENT_RE = re.compile(r"^obligation\.([a-z0-9]+(-[a-z0-9]+)*)\.([a-z0-9]+(-[a-z0-9]+)*)$")

# Schema version of the obligation documents this code validates.
# ``law-map validate`` rejects anything else with a migrate prompt.
SCHEMA_VERSION = 2

# The category vocabulary is defined once, here. ``schemas/obligation.schema.yml``
# documents it; ``stats`` renders it. ``accessibility`` covers obligations
# grounded in accessibility law (e.g. the European Accessibility Act), which
# must not be filed under ``privacy``.
CATEGORIES = {"privacy", "security", "copyright", "ai", "licensing", "telemetry", "crypto", "accessibility"}
MODALITIES = {"obligation", "prohibition", "permission"}
SEVERITIES = {"info", "advisory", "high", "critical"}
SOURCE_TYPES = {
    "statute",
    "regulation",
    "precedent",
    "guidance",
    "standard",
    "model_code",
    # Not legal sources: a private body's rules (contest terms, platform
    # policies) and a documented incident whose lesson grounds the practice.
    "private_rule",
    "incident_report",
}
# How close a grounding's sources are to the instrument itself. ``primary``
# is the instrument from its publisher (gazette, EUR-Lex ELI URL, slip
# opinion); ``official-secondary`` is an authority's own commentary or
# guidance page about it; ``unofficial`` is any third-party copy, archive
# snapshot, or write-up. Every obligation needs at least one ``primary``
# grounding (see :mod:`law_map.validate`).
SOURCE_KINDS = {"primary", "official-secondary", "unofficial"}
# Hosts whose copies are never the instrument itself: mark groundings citing
# them ``unofficial``. Used by ``law-map migrate`` and as a validation
# warning when paired with a loftier ``source_kind``.
UNOFFICIAL_HOSTS = ("web.archive.org", "dsgvo-gesetz.de", "law.justia.com")
# Corpus packs by binding level, strongest first. ``core`` holds binding law
# (statutes, regulations, case law), ``guidance`` official guidance and
# standards, ``community`` private rules and incident lessons.
PACKS = ("core", "guidance", "community")
SOURCE_TYPE_PACK = {
    "statute": "core",
    "regulation": "core",
    "precedent": "core",
    "guidance": "guidance",
    "standard": "guidance",
    "model_code": "guidance",
    "private_rule": "community",
    "incident_report": "community",
}
# withdrawn: no longer issued or endorsed by its authority (rescinded,
# revoked, or taken down with a change of administration) — kept only as
# historical context, never as a current basis for an obligation.
STATUSES = {"in_force", "scheduled", "proposed", "superseded", "withdrawn"}
ENFORCEMENT_LEVELS = {"L0", "L1", "L2"}
# How hard a grounding binds, for functional-equivalence honesty: ``binding``
# (statute/regulation/case law in force), ``persuasive`` (official guidance
# and standards), ``background`` (withdrawn context, incident lessons, and
# other non-binding material). Optional per grounding.
STRENGTHS = {"binding", "persuasive", "background"}
# How sure the grounding -> obligation mapping is (PHI-3: functional
# equivalence presumes similarity too readily): ``high`` (the cited text
# itself requires the obligation's behaviour), ``medium`` (requires it in
# substance, but scope/exceptions/strength diverge materially), ``low``
# (supports it only by analogy or inference). Optional per grounding.
CONFIDENCES = {"high", "medium", "low"}
# Grounding jurisdictions are ISO 3166-1 alpha-2 codes; EU (an ISO
# "exceptionally reserved" code) is the one documented non-country
# exception. Common non-ISO aliases are rejected with the ISO code to use.
JURISDICTION_RE = re.compile(r"^[A-Z]{2}$")
JURISDICTION_ALIASES = {"UK": "GB"}


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
    # Valid obligations outside the packs selected at load time: still
    # validated and resolvable as requires/conflicts targets, never listed.
    excluded: list[Obligation] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def ok(self) -> bool:
        return not self.errors

    @property
    def all_obligations(self) -> list[Obligation]:
        """Selected and excluded obligations: the whole validated corpus."""
        return [*self.obligations, *self.excluded]


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


def obligation_pack(ob: Obligation) -> str:
    """The pack of the strongest grounding: ``core`` beats ``guidance`` beats ``community``.

    An obligation with no recognisable ``source_type`` falls back to
    ``community``; validation reports the bad enum separately.
    """
    packs = {SOURCE_TYPE_PACK.get(str(g.get("source_type")), "community") for g in obligation_groundings(ob)}
    return next((p for p in PACKS if p in packs), "community")


def iter_groundings(corpus: Corpus) -> Iterator[dict[str, Any]]:
    """Every mapping grounding in the corpus, in obligation order."""
    for ob in corpus.obligations:
        yield from obligation_groundings(ob)


def is_valid_jurisdiction(code: object) -> bool:
    """True for ISO 3166-1 alpha-2 codes plus the single ``EU`` exception."""
    if not isinstance(code, str) or not JURISDICTION_RE.match(code):
        return False
    if code == "EU":
        return True
    return pycountry.countries.get(alpha_2=code) is not None


def is_valid_subdivision(jurisdiction: object, subdivision: object) -> bool:
    """True when ``{jurisdiction}-{subdivision}`` is an ISO 3166-2 code."""
    if not isinstance(jurisdiction, str) or not isinstance(subdivision, str):
        return False
    if not subdivision.strip():
        return False
    return pycountry.subdivisions.get(code=f"{jurisdiction}-{subdivision}") is not None  # type: ignore[no-untyped-call]


def _review_complete(reviewed_by: object, reviewed_on: object) -> bool:
    """True when a ``reviewed_by`` handle+domain mapping and an ISO ``reviewed_on`` date are both present."""
    if not isinstance(reviewed_by, dict):
        return False
    handle = reviewed_by.get("handle")
    domain = reviewed_by.get("domain")
    if not isinstance(handle, str) or not handle.strip():
        return False
    if not isinstance(domain, str) or not domain.strip():
        return False
    return parse_iso_date(reviewed_on) is not None


def obligation_review_status(ob: Obligation) -> str:
    """``reviewed`` when the obligation records a reviewer and a review date, else ``draft``."""
    if _review_complete(ob.data.get("reviewed_by"), ob.data.get("reviewed_on")):
        return "reviewed"
    return "draft"


def grounding_review_status(g: dict[str, Any]) -> str:
    """``reviewed`` when the grounding records a reviewer and a review date, else ``draft``."""
    if _review_complete(g.get("reviewed_by"), g.get("reviewed_on")):
        return "reviewed"
    return "draft"


_COMPAT_EXPORTS: dict[str, str] = {
    "load_corpus": "law_map.loader",
    "check_unique_ids": "law_map.validate",
    "validate_obligation_document": "law_map.validate",
    "check_cross_references": "law_map.refs",
    "CODEX_SECTIONS_DIR": "law_map.kanon",
    "codex_section_path": "law_map.kanon",
    "check_codex_sections": "law_map.kanon",
    "check_codex_coverage": "law_map.kanon",
    "unresolved_section_error": "law_map.kanon",
}


def __getattr__(name: str) -> object:
    """Backward-compatible facade for the pre-split ``model`` surface.

    Canonical homes are :mod:`law_map.loader` (``load_corpus``),
    :mod:`law_map.validate` (single-file checks), :mod:`law_map.refs`
    (cross-file checks), and :mod:`law_map.kanon` (codex linkage).
    Lazy import keeps the ``model -> validate -> model`` cycle unobservable.
    """
    if name in _COMPAT_EXPORTS:
        import importlib

        return getattr(importlib.import_module(_COMPAT_EXPORTS[name]), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
