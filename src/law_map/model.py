"""Corpus loading and validation for law-map obligations.

The corpus lives in ``obligations/<domain>/<slug>.yml``. Files whose basename
starts with ``_`` are excluded (e.g. ``_example.yml``). Validation collects
every problem it can find instead of raising on the first one; callers decide
whether errors are fatal.
"""

from __future__ import annotations

import re
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


def _is_valid_url(value: object) -> bool:
    return isinstance(value, str) and value.startswith(("http://", "https://"))


def _is_iso_date(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _check_str(data: dict[str, Any], key: str, errors: list[str], required: bool = True) -> bool:
    if key not in data or data[key] is None:
        if required:
            errors.append(f"missing required field '{key}'")
        return False
    if not isinstance(data[key], str) or not data[key].strip():
        errors.append(f"field '{key}' must be a non-empty string")
        return False
    return True


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
    _check_str(g, "jurisdiction", errors)
    _check_str(g, "authority", errors)
    _check_str(g, "citation", errors)
    _check_str(g, "review_by", errors)
    if "review_by" in g and not _is_iso_date(g.get("review_by")):
        errors.append(f"{where}.review_by must be an ISO date (YYYY-MM-DD), got {g.get('review_by')!r}")
    if "effective" in g and not _is_iso_date(g.get("effective")):
        errors.append(f"{where}.effective must be an ISO date, got {g.get('effective')!r}")

    st = g.get("source_type")
    if not isinstance(st, str) or st not in SOURCE_TYPES:
        errors.append(f"{where}.source_type must be one of {sorted(SOURCE_TYPES)}, got {st!r}")
    status = g.get("status")
    if not isinstance(status, str) or status not in STATUSES:
        errors.append(f"{where}.status must be one of {sorted(STATUSES)}, got {status!r}")

    sources = g.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append(f"{where}.sources must be a non-empty list of URLs")
    elif not all(_is_valid_url(s) for s in sources):
        errors.append(f"{where}.sources must contain only http/https URLs")


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

    enforcement = data.get("enforcement")
    if enforcement is not None:
        if not isinstance(enforcement, dict):
            errors.append("enforcement must be a mapping")
            return
        level = enforcement.get("level")
        if not isinstance(level, str) or level not in ENFORCEMENT_LEVELS:
            errors.append(f"enforcement.level must be one of {sorted(ENFORCEMENT_LEVELS)}, got {level!r}")


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


def load_corpus(root: Path) -> Corpus:
    """Load every non-underscore obligation file under root (recursive).

    Returns a Corpus with per-file validation issues in ``errors``; never
    raises on bad content. ``root`` may be missing (empty corpus).
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
        _validate_obligation(data, corpus.errors, corpus.warnings)
        corpus.obligations.append(Obligation(path=path, data=data))
    _check_uniqueness(corpus)
    return corpus


def _validate_obligation(data: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    if data.get("version") != 1:
        errors.append("version must be 1 (got {!r})".format(data.get("version")))
    _check_id(data, errors)
    _check_domain_slug(data, errors)
    for key in ("title", "summary"):
        _check_str(data, key, errors)
    category = data.get("category")
    if not isinstance(category, str) or category not in CATEGORIES:
        errors.append(f"category must be one of {sorted(CATEGORIES)}, got {category!r}")
    modality = data.get("modality")
    if not isinstance(modality, str) or modality not in MODALITIES:
        errors.append(f"modality must be one of {sorted(MODALITIES)}, got {modality!r}")
    severity = data.get("severity")
    if not isinstance(severity, str) or severity not in SEVERITIES:
        errors.append(f"severity must be one of {sorted(SEVERITIES)}, got {severity!r}")

    scope = data.get("scope")
    if not isinstance(scope, dict):
        errors.append("scope must be a mapping")
    else:
        if "components" in scope and not isinstance(scope["components"], list):
            errors.append("scope.components must be a list")
        if "data_types" in scope and not isinstance(scope["data_types"], list):
            errors.append("scope.data_types must be a list")

    groundings = data.get("groundings")
    if not isinstance(groundings, list) or not groundings:
        errors.append("groundings must be a non-empty list")
    else:
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

    for key in ("conflicts", "requires"):
        value = data.get(key, [])
        if not isinstance(value, list):
            errors.append(f"{key} must be a list")
        elif not all(isinstance(x, str) for x in value):
            errors.append(f"{key} must contain only obligation ids")

    _validate_directives(data, errors)

    related = data.get("related_sections", [])
    if isinstance(related, list) and not all(isinstance(x, str) for x in related):
        errors.append("related_sections must contain only strings")

    enforcement = data.get("enforcement")
    if enforcement is not None and isinstance(enforcement, dict):
        refs = enforcement.get("check_refs", [])
        if not isinstance(refs, list):
            errors.append("enforcement.check_refs must be a list")


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


def check_cross_references(corpus: Corpus, checks_root: Path | None = None) -> None:
    """Cross-file checks: check_refs targets and requires/conflicts ids.

    Runs after load_corpus; appends to the corpus's error/warning lists.
    ``checks_root`` may be None to skip check_refs resolution (export/check
    commands operate on obligations only).
    """
    known_ids = {ob.id for ob in corpus.obligations if ob.id}
    section_users: dict[str, int] = {}
    for ob in corpus.obligations:
        for section in ob.data.get("related_sections", []):
            if isinstance(section, str):
                section_users[section] = section_users.get(section, 0) + 1
    for ob in corpus.obligations:
        for dep in ob.data.get("requires", []):
            if dep not in known_ids:
                corpus.errors.append(f"{ob.id}: requires '{dep}' does not exist in corpus")
        for conflict in ob.data.get("conflicts", []):
            if conflict not in known_ids:
                corpus.errors.append(f"{ob.id}: conflicts '{conflict}' does not exist in corpus")
        related = ob.data.get("related_sections", [])
        if isinstance(related, list):
            for section in related:
                if isinstance(section, str) and section_users.get(section, 0) < 2:
                    corpus.warnings.append(
                        f"{ob.id}: related_sections '{section}' is referenced by no other obligation "
                        "(possibly unknown to good-future-codex)"
                    )
        if checks_root is not None:
            enforcement = ob.data.get("enforcement")
            if isinstance(enforcement, dict):
                for ref in enforcement.get("check_refs", []):
                    if not _check_exists(checks_root, ref):
                        corpus.errors.append(
                            f"{ob.id}: enforcement.check_refs '{ref}' does not match checks/{ref}.yml"
                        )


def _check_exists(checks_root: Path, ref: str) -> bool:
    target = Path(checks_root) / f"{ref}.yml"
    return target.is_file()