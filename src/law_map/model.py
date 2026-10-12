"""Corpus loading and validation for law-map obligations.

The corpus lives in ``obligations/<domain>/<slug>.yml``. Files whose basename
starts with ``_`` are excluded (e.g. ``_example.yml``). Validation collects
every problem it can find instead of raising on the first one; callers decide
whether errors are fatal.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import yaml

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


def _is_valid_url(value: object) -> bool:
    return isinstance(value, str) and value.startswith(("http://", "https://"))


def _check_str(data: dict[str, Any], key: str, errors: list[str], required: bool = True) -> bool:
    if key not in data or data[key] is None:
        if required:
            errors.append(f"missing required field '{key}'")
        return False
    if not isinstance(data[key], str) or not data[key].strip():
        errors.append(f"field '{key}' must be a non-empty string")
        return False
    return True


def _check_one_of(
    data: dict[str, Any], key: str, allowed: set[str], errors: list[str], where: str = ""
) -> None:
    """Enum membership check with the shared ``must be one of [...]`` wording."""
    value = data.get(key)
    if not isinstance(value, str) or value not in allowed:
        prefix = f"{where}." if where else ""
        errors.append(f"{prefix}{key} must be one of {sorted(allowed)}, got {value!r}")


def _check_id_list(data: dict[str, Any], key: str, errors: list[str]) -> None:
    """Obligation-id list check (the ``conflicts``/``requires`` wording)."""
    value = data.get(key, [])
    if not isinstance(value, list):
        errors.append(f"{key} must be a list")
    elif not all(isinstance(x, str) for x in value):
        errors.append(f"{key} must contain only obligation ids")


def _check_iso_date(
    data: dict[str, Any], key: str, where: str, errors: list[str], detail: str
) -> None:
    """ISO date check for an optional grounding date field (skipped when absent)."""
    if key in data and parse_iso_date(data.get(key)) is None:
        errors.append(f"{where}.{key} must be {detail}, got {data.get(key)!r}")


def _check_id(data: dict[str, Any], errors: list[str]) -> None:
    value = data.get("id")
    if not isinstance(value, str) or not value.strip():
        errors.append("id must be a non-empty string")
        return
    if not IDENT_RE.match(value):
        errors.append(
            f"id '{value}' does not match pattern obligation.<domain>.<slug> "
            "(lowercase alphanumeric segments separated by dots/hyphens)"
        )


def _check_domain_slug(data: dict[str, Any], errors: list[str]) -> None:
    value = data.get("id")
    if not isinstance(value, str):
        return
    match = IDENT_RE.match(value)
    if not match:
        return
    expected_dir = match.group(1)
    path = data.get("_path")
    if path and path.parent.name != expected_dir:
        errors.append(
            f"id domain '{expected_dir}' does not match directory '{path.parent.name}'"
        )


def _validate_grounding(g: dict[str, Any], errors: list[str], gindex: int) -> None:
    where = f"groundings[{gindex}]"
    for key in ("jurisdiction", "authority", "citation", "review_by"):
        _check_str(g, key, errors)
    _check_iso_date(g, "review_by", where, errors, "an ISO date (YYYY-MM-DD)")
    _check_iso_date(g, "effective", where, errors, "an ISO date")

    _check_one_of(g, "source_type", SOURCE_TYPES, errors, where)
    _check_one_of(g, "status", STATUSES, errors, where)

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
    _check_one_of(enforcement, "level", ENFORCEMENT_LEVELS, errors, "enforcement")
    refs = enforcement.get("check_refs", [])
    if not isinstance(refs, list):
        errors.append("enforcement.check_refs must be a list")


def _parse_yaml(path: Path, errors: list[str]) -> dict[str, Any] | None:
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
    data.setdefault("_path", path)
    return data


def load_corpus(root: Path, today: date | None = None) -> Corpus:
    """Load every non-underscore obligation file under root (recursive).

    Returns a Corpus with per-file validation issues in ``errors``; never
    raises on bad content. ``root`` may be missing (empty corpus). ``today``
    pins the date for scheduled-effective warnings (defaults to today).
    """
    corpus = Corpus()
    root = Path(root)
    if not root.is_dir():
        return corpus
    for path in sorted(root.rglob("*.yml")):
        if path.name.startswith("_"):
            continue
        data = _parse_yaml(path, corpus.errors)
        if data is None:
            continue
        _validate_obligation(data, corpus.errors, corpus.warnings, today=today)
        corpus.obligations.append(Obligation(path=path, data=data))
    _check_uniqueness(corpus)
    return corpus


def _validate_identity(data: dict[str, Any], errors: list[str]) -> None:
    if data.get("version") != 1:
        errors.append("version must be 1 (got {!r})".format(data.get("version")))
    _check_id(data, errors)
    _check_domain_slug(data, errors)
    for key in ("title", "summary"):
        _check_str(data, key, errors)
    _check_one_of(data, "category", CATEGORIES, errors)
    _check_one_of(data, "modality", MODALITIES, errors)
    _check_one_of(data, "severity", SEVERITIES, errors)


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
        _check_id_list(data, key, errors)


def _validate_related_sections(data: dict[str, Any], errors: list[str]) -> None:
    related = data.get("related_sections", [])
    if isinstance(related, list) and not all(isinstance(x, str) for x in related):
        errors.append("related_sections must contain only strings")


def _validate_obligation(
    data: dict[str, Any], errors: list[str], warnings: list[str], today: date | None = None
) -> None:
    _validate_identity(data, errors)
    _validate_scope(data, errors)
    _validate_groundings(data, errors, warnings)
    _validate_relations(data, errors)
    _validate_directives(data, errors)
    _validate_enforcement(data, errors)
    _validate_related_sections(data, errors)
    _check_spec_warnings(data, warnings, today or date.today())


def _check_spec_warnings(data: dict[str, Any], warnings: list[str], today: date) -> None:
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


def _check_uniqueness(corpus: Corpus) -> None:
    seen: dict[str, Path] = {}
    for ob in corpus.obligations:
        ob_id = ob.id
        if not ob_id:
            continue
        if ob_id in seen:
            corpus.errors.append(
                f"duplicate id '{ob_id}' in {seen[ob_id]} and {ob.path}"
            )
        else:
            seen[ob_id] = ob.path


CODEX_SECTIONS_DIR = "sections"


def codex_section_path(codex_root: Path, section_id: str) -> Path | None:
    """Map a ``related_sections`` id to its codex file per the ``<tier>-<slug>`` rule.

    ``baseline-personal-data`` resolves to
    ``sections/baseline/personal-data.md.jinja``: the id's first segment is
    the tier directory, the rest the slug. The tier segment must name an
    existing directory under ``sections/`` — ids like ``personal-data``
    (``personal`` is not a codex tier) resolve to None, as do ids with no
    separator or an empty slug.
    """
    tier, sep, slug = section_id.partition("-")
    if not sep or not tier or not slug:
        return None
    tier_dir = Path(codex_root) / CODEX_SECTIONS_DIR / tier
    if not tier_dir.is_dir():
        return None
    return tier_dir / f"{slug}.md.jinja"


def _codex_unresolved_error(ob_id: str, section: str) -> str:
    """Shared wording for a ``related_sections`` id that resolves nowhere."""
    return (
        f"{ob_id}: related_sections '{section}' does not resolve to a "
        "good-future-codex section (expected sections/<tier>/<slug>.md.jinja, "
        "e.g. baseline-personal-data -> sections/baseline/personal-data.md.jinja)"
    )


def check_codex_sections(corpus: Corpus, codex_root: Path) -> list[str]:
    """Verify every ``related_sections`` id resolves inside a codex checkout.

    Per the ``<tier>-<slug>`` naming rule each id must map to an *existing*
    ``sections/<tier>/<slug>.md.jinja`` in good-future-codex; anything else
    is an error, not a warning. Returns a list of error strings (empty when
    the corpus is consistent with the checkout). Never raises: a missing or
    wrong-shaped checkout surfaces as per-id errors.
    """
    root = Path(codex_root)
    errors: list[str] = []
    for ob in corpus.obligations:
        related = ob.data.get("related_sections", [])
        if not isinstance(related, list):
            continue
        for section in related:
            if not isinstance(section, str):
                continue  # non-strings already error in per-file validation
            target = codex_section_path(root, section)
            if target is None or not target.is_file():
                errors.append(_codex_unresolved_error(ob.id, section))
    return errors


def check_codex_coverage(corpus: Corpus, codex_root: Path) -> list[str]:
    """Warn for codex sections that no obligation references (reverse coverage).

    Enumerates ``sections/<tier>/<slug>.md.jinja`` per the ``<tier>-<slug>``
    naming rule and reports every id absent from all obligations'
    ``related_sections``. Warnings only, never errors: the codex is
    legitimately broader than the obligation graph. Never raises — a
    missing checkout yields no warnings (the forward check reports errors).
    """
    referenced: set[str] = set()
    for ob in corpus.obligations:
        related = ob.data.get("related_sections", [])
        if isinstance(related, list):
            for section in related:
                if isinstance(section, str):
                    referenced.add(section)
    warnings: list[str] = []
    sections = Path(codex_root) / CODEX_SECTIONS_DIR
    if not sections.is_dir():
        return warnings
    for tier_dir in sorted(p for p in sections.iterdir() if p.is_dir()):
        for path in sorted(tier_dir.glob("*.md.jinja")):
            if path.name.startswith("_"):
                continue
            section_id = f"{tier_dir.name}-{path.name.removesuffix('.md.jinja')}"
            if section_id not in referenced:
                warnings.append(
                    f"codex section '{section_id}' has no referencing obligation "
                    "(no related_sections points at it)"
                )
    return warnings


def _count_section_users(corpus: Corpus) -> dict[str, int]:
    """How many obligations reference each ``related_sections`` id."""
    users: dict[str, int] = {}
    for ob in corpus.obligations:
        for section in ob.data.get("related_sections", []):
            if isinstance(section, str):
                users[section] = users.get(section, 0) + 1
    return users


def _check_obligation_refs(
    ob: Obligation,
    known_ids: set[str],
    section_users: dict[str, int],
    corpus: Corpus,
    checks_root: Path | None,
    codex_root: Path | None,
) -> None:
    for dep in ob.data.get("requires", []):
        if dep not in known_ids:
            corpus.errors.append(f"{ob.id}: requires '{dep}' does not exist in corpus")
    for conflict in ob.data.get("conflicts", []):
        if conflict not in known_ids:
            corpus.errors.append(f"{ob.id}: conflicts '{conflict}' does not exist in corpus")
    related = ob.data.get("related_sections", [])
    if isinstance(related, list):
        for section in related:
            if not isinstance(section, str):
                continue
            if codex_root is not None:
                target = codex_section_path(codex_root, section)
                if target is None or not target.is_file():
                    corpus.errors.append(_codex_unresolved_error(ob.id, section))
            elif section_users.get(section, 0) < 2:
                corpus.warnings.append(
                    f"{ob.id}: related_sections '{section}' is referenced by no other obligation "
                    f"(possibly unknown to good-future-codex; run 'law-map check --codex <checkout>' "
                    "for a definitive resolution check)"
                )
    if checks_root is not None:
        enforcement = ob.data.get("enforcement")
        if isinstance(enforcement, dict):
            for ref in enforcement.get("check_refs", []):
                if not _check_exists(checks_root, ref):
                    corpus.errors.append(
                        f"{ob.id}: enforcement.check_refs '{ref}' does not match checks/{ref}.yml"
                    )


def check_cross_references(
    corpus: Corpus,
    checks_root: Path | None = None,
    codex_root: Path | None = None,
) -> None:
    """Cross-file checks: check_refs targets and requires/conflicts ids.

    Runs after load_corpus; appends to the corpus's error/warning lists.
    ``checks_root`` may be None to skip check_refs resolution (export/check
    commands operate on obligations only).

    With ``codex_root`` (a good-future-codex checkout) every
    ``related_sections`` id must resolve to ``sections/<tier>/<slug>.md.jinja``
    per the ``<tier>-<slug>`` naming rule — missing ids are errors and the
    weak "referenced by no other obligation" warning is suppressed. Sections
    no obligation references become warnings via :func:`check_codex_coverage`.
    Without it, the lenient offline warning behavior is kept.
    """
    known_ids = {ob.id for ob in corpus.obligations if ob.id}
    section_users = _count_section_users(corpus)
    for ob in corpus.obligations:
        _check_obligation_refs(ob, known_ids, section_users, corpus, checks_root, codex_root)
    if codex_root is not None:
        corpus.warnings.extend(check_codex_coverage(corpus, codex_root))


def _check_exists(checks_root: Path, ref: str) -> bool:
    target = Path(checks_root) / f"{ref}.yml"
    return target.is_file()
