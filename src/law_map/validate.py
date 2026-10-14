"""Single-obligation validation for the law-map corpus.

Pure content checks: every problem is appended to ``errors`` (fatal) or
``warnings`` (non-fatal) instead of raising, so callers can report the
whole corpus state at once. Cross-file checks (``requires``/``conflicts``
id existence, ``check_refs`` files, kanon sections) live in
:mod:`law_map.refs` and :mod:`law_map.kanon`; file discovery and
orchestration live in :mod:`law_map.model`.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .model import (
    CATEGORIES,
    ENFORCEMENT_LEVELS,
    IDENT_RE,
    JURISDICTION_ALIASES,
    JURISDICTION_RE,
    MODALITIES,
    SEVERITIES,
    SOURCE_TYPES,
    STATUSES,
    SUBDIVISION_JURISDICTIONS,
    Corpus,
    parse_iso_date,
)

__all__ = ["check_unique_ids", "validate_obligation_document"]


def validate_obligation_document(
    data: dict[str, Any],
    *,
    path: Path,
    errors: list[str],
    warnings: list[str],
    today: date | None = None,
) -> None:
    """Run every single-file check for one obligation document."""
    _validate_identity(data, path, errors)
    _validate_scope(data, errors)
    _validate_groundings(data, errors, warnings)
    _validate_relations(data, errors)
    _validate_directives(data, errors)
    _validate_enforcement(data, errors)
    _validate_related_sections(data, errors)
    _warn_archive_sources(data, warnings)
    _warn_spec_gaps(data, warnings, today or date.today())


def check_unique_ids(corpus: Corpus) -> None:
    """Corpus-level check: every obligation id must be unique."""
    seen: dict[str, Path] = {}
    for ob in corpus.all_obligations:
        ob_id = ob.id
        if not ob_id:
            continue
        if ob_id in seen:
            corpus.errors.append(f"duplicate id '{ob_id}' in {seen[ob_id]} and {ob.path}")
        else:
            seen[ob_id] = ob.path


def _is_valid_url(value: object) -> bool:
    return isinstance(value, str) and value.startswith(("http://", "https://"))


def _require_text(data: dict[str, Any], key: str, errors: list[str]) -> bool:
    if key not in data or data[key] is None:
        errors.append(f"missing required field '{key}'")
        return False
    if not isinstance(data[key], str) or not data[key].strip():
        errors.append(f"field '{key}' must be a non-empty string")
        return False
    return True


def _require_one_of(
    data: dict[str, Any], key: str, allowed: set[str], errors: list[str], where: str = ""
) -> None:
    """Enum membership check with the shared ``must be one of [...]`` wording."""
    value = data.get(key)
    if not isinstance(value, str) or value not in allowed:
        prefix = f"{where}." if where else ""
        errors.append(f"{prefix}{key} must be one of {sorted(allowed)}, got {value!r}")


def _require_id_list(data: dict[str, Any], key: str, errors: list[str]) -> None:
    """Obligation-id list check (the ``conflicts``/``requires`` wording)."""
    value = data.get(key, [])
    if not isinstance(value, list):
        errors.append(f"{key} must be a list")
    elif not all(isinstance(x, str) for x in value):
        errors.append(f"{key} must contain only obligation ids")


def _require_iso_date(
    data: dict[str, Any], key: str, where: str, errors: list[str], detail: str
) -> None:
    """ISO date check for an optional grounding date field (skipped when absent)."""
    if key in data and parse_iso_date(data.get(key)) is None:
        errors.append(f"{where}.{key} must be {detail}, got {data.get(key)!r}")


def _validate_obligation_id(data: dict[str, Any], errors: list[str]) -> None:
    value = data.get("id")
    if not isinstance(value, str) or not value.strip():
        errors.append("id must be a non-empty string")
        return
    if not IDENT_RE.match(value):
        errors.append(
            f"id '{value}' does not match pattern obligation.<domain>.<slug> "
            "(lowercase alphanumeric segments separated by dots/hyphens)"
        )


def _validate_id_directory(data: dict[str, Any], path: Path, errors: list[str]) -> None:
    value = data.get("id")
    if not isinstance(value, str):
        return
    match = IDENT_RE.match(value)
    if not match:
        return
    expected_dir = match.group(1)
    if path.parent.name != expected_dir:
        errors.append(f"id domain '{expected_dir}' does not match directory '{path.parent.name}'")


def _validate_grounding(g: dict[str, Any], errors: list[str], index: int) -> None:
    where = f"groundings[{index}]"
    for key in ("jurisdiction", "authority", "citation", "review_by"):
        _require_text(g, key, errors)
    _validate_jurisdiction(g.get("jurisdiction"), where, errors)
    _require_iso_date(g, "review_by", where, errors, "an ISO date (YYYY-MM-DD)")
    _require_iso_date(g, "effective", where, errors, "an ISO date")
    _require_iso_date(g, "reviewed_on", where, errors, "an ISO date")

    _require_one_of(g, "source_type", SOURCE_TYPES, errors, where)
    _require_one_of(g, "status", STATUSES, errors, where)

    sources = g.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append(f"{where}.sources must be a non-empty list of URLs")
    elif not all(_is_valid_url(s) for s in sources):
        errors.append(f"{where}.sources must contain only http/https URLs")

    ref = g.get("open_law")
    if ref is not None:
        if not isinstance(ref, dict):
            errors.append(f"{where}.open_law must be a mapping with 'source' and 'id'")
        else:
            for key in ("source", "id"):
                value = ref.get(key)
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"{where}.open_law.{key} must be a non-empty string")


def _validate_jurisdiction(value: object, where: str, errors: list[str]) -> None:
    """ISO 3166-1 alpha-2 (or the ``EU`` exception); aliases such as ``UK`` name their ISO code."""
    if not isinstance(value, str) or not value.strip():
        return  # missing/empty is reported by _require_text
    if value in JURISDICTION_ALIASES:
        errors.append(
            f"{where}.jurisdiction {value!r} is not ISO 3166-1; use {JURISDICTION_ALIASES[value]!r}"
        )
    elif not JURISDICTION_RE.match(value):
        errors.append(
            f"{where}.jurisdiction must be an ISO 3166-1 alpha-2 code or 'EU', got {value!r}"
        )


def _validate_directives(data: dict[str, Any], errors: list[str]) -> None:
    directives = data.get("directives")
    if directives is None:
        return
    if not isinstance(directives, dict):
        errors.append("directives must be a mapping")
        return
    for key in ("human", "agent"):
        if key not in directives:
            errors.append(f"directives is missing required key '{key}'")


def _validate_enforcement(data: dict[str, Any], errors: list[str]) -> None:
    enforcement = data.get("enforcement")
    if enforcement is None:
        return
    if not isinstance(enforcement, dict):
        errors.append("enforcement must be a mapping")
        return
    _require_one_of(enforcement, "level", ENFORCEMENT_LEVELS, errors, "enforcement")
    refs = enforcement.get("check_refs", [])
    if not isinstance(refs, list):
        errors.append("enforcement.check_refs must be a list")


def _validate_identity(data: dict[str, Any], path: Path, errors: list[str]) -> None:
    if data.get("version") != 1:
        errors.append("version must be 1 (got {!r})".format(data.get("version")))
    _validate_obligation_id(data, errors)
    _validate_id_directory(data, path, errors)
    for key in ("title", "summary"):
        _require_text(data, key, errors)
    _require_one_of(data, "category", CATEGORIES, errors)
    _require_one_of(data, "modality", MODALITIES, errors)
    _require_one_of(data, "severity", SEVERITIES, errors)


def _validate_scope(data: dict[str, Any], errors: list[str]) -> None:
    scope = data.get("scope")
    if not isinstance(scope, dict):
        errors.append("scope must be a mapping")
        return
    for key in ("components", "data_types"):
        if key in scope and not isinstance(scope[key], list):
            errors.append(f"scope.{key} must be a list")


def _validate_groundings(data: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    groundings = data.get("groundings")
    if not isinstance(groundings, list) or not groundings:
        errors.append("groundings must be a non-empty list")
        return
    for i, g in enumerate(groundings):
        if not isinstance(g, dict):
            errors.append(f"groundings[{i}] must be a mapping")
            continue
        if g.get("subdivision"):
            jurisdiction = g.get("jurisdiction")
            if not isinstance(jurisdiction, str) or jurisdiction not in SUBDIVISION_JURISDICTIONS:
                warnings.append(
                    f"groundings[{i}].subdivision only allowed for "
                    f"{sorted(SUBDIVISION_JURISDICTIONS)}; got jurisdiction {jurisdiction!r}"
                )
        _validate_grounding(g, errors, i)


def _validate_relations(data: dict[str, Any], errors: list[str]) -> None:
    for key in ("conflicts", "requires"):
        _require_id_list(data, key, errors)


def _validate_related_sections(data: dict[str, Any], errors: list[str]) -> None:
    related = data.get("related_sections", [])
    if isinstance(related, list) and not all(isinstance(x, str) for x in related):
        errors.append("related_sections must contain only strings")


def _is_archive_url(url: str) -> bool:
    """True for web-archive snapshots and archived US government sites.

    ``*.archives.gov`` subdomains hold frozen sites of past administrations
    (e.g. ``bidenwhitehouse.archives.gov``); ``www.archives.gov`` is NARA's
    own live site and is not flagged.
    """
    host = (urlparse(url).hostname or "").lower()
    return host == "web.archive.org" or (host.endswith(".archives.gov") and host != "www.archives.gov")


def _warn_archive_sources(data: dict[str, Any], warnings: list[str]) -> None:
    """Warn on groundings sourced from an archive site: the instrument may be withdrawn."""
    ob_id = data.get("id", "?")
    groundings = data.get("groundings")
    if not isinstance(groundings, list):
        return
    for i, g in enumerate(groundings):
        sources = g.get("sources") if isinstance(g, dict) else None
        if not isinstance(sources, list):
            continue
        for url in sources:
            if not (isinstance(url, str) and _is_archive_url(url)):
                continue
            if g.get("status") == "withdrawn":
                advice = "status 'withdrawn': historical context only, not a current basis"
            else:
                advice = "confirm the instrument is still current or mark it 'withdrawn'"
            warnings.append(f"{ob_id}: groundings[{i}] cites archive site {url} — {advice}")


def _warn_spec_gaps(data: dict[str, Any], warnings: list[str], today: date) -> None:
    """Non-fatal notices: scheduled-but-already-effective and spec-less obligations.

    The spec-less predicate is ``enforcement.check_refs`` emptiness only —
    an obligation without a machine-check spec warns until a
    ``checks/<domain>/<slug>.yml`` spec exists, whatever its level.
    """
    ob_id = data.get("id", "?")
    groundings = data.get("groundings")
    if isinstance(groundings, list):
        for i, g in enumerate(groundings):
            if not isinstance(g, dict) or g.get("status") != "scheduled":
                continue
            effective = parse_iso_date(g.get("effective"))
            if effective is None:
                continue  # malformed dates are errors, reported elsewhere
            if effective <= today:
                warnings.append(
                    f"{ob_id}: groundings[{i}] status is 'scheduled' but effective "
                    f"{g.get('effective')} is already past (in force?)"
                )
    enforcement = data.get("enforcement")
    refs = enforcement.get("check_refs") if isinstance(enforcement, dict) else None
    if refs is None or (isinstance(refs, list) and not refs):
        warnings.append(
            f"{ob_id}: no enforcement.check_refs — spec-less obligation "
            "(prose-only until a checks/<domain>/<slug>.yml spec exists)"
        )
