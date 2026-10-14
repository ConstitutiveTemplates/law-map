"""Loading and validation for ``checks/<domain>/<slug>.yml`` machine-check specs.

Obligation documents point at specs through ``enforcement.check_refs``
(existence of the target file is checked in :mod:`law_map.refs`); this
module validates spec *content*: the ``id``/``obligation``/``level``
shape, ``id`` matching the file path, ``level`` in the enforcement
vocabulary, the ``obligation`` ref resolving into the corpus, every
``triggers`` entry compiling as a regex, one spec per obligation, and —
for ``L2`` hard gates — an executable rule (``blocking`` wiring) plus
``fixtures`` that exist. Problems land in ``corpus.errors`` so
``law-map validate`` fails on them, and daimonion consumes the same
``triggers`` field via ``--rules <checks-dir>``.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from .model import ENFORCEMENT_LEVELS, Corpus

__all__ = ["validate_check_spec", "validate_check_specs"]


def validate_check_specs(checks_root: Path, corpus: Corpus) -> None:
    """Parse and validate every check spec under ``checks_root``.

    Never raises on bad content — problems land in ``corpus.errors``.
    Files whose basename starts with ``_`` are skipped, mirroring the
    obligations loader. A missing ``checks_root`` is quietly ignored so
    commands operating on obligations only keep working.
    """
    checks_root = Path(checks_root)
    if not checks_root.is_dir():
        return
    known_ids = {ob.id for ob in corpus.all_obligations if ob.id}
    seen: dict[str, Path] = {}
    for path in sorted(checks_root.rglob("*.yml")):
        if path.name.startswith("_"):
            continue
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except OSError as exc:
            corpus.errors.append(f"cannot read {path}: {exc}")
            continue
        except yaml.YAMLError as exc:
            corpus.errors.append(f"invalid YAML in {path}: {exc}")
            continue
        if not isinstance(data, dict):
            corpus.errors.append(f"{path}: document must be a mapping, got {type(data).__name__}")
            continue
        validate_check_spec(data, path=path, errors=corpus.errors, known_ids=known_ids, repo_root=checks_root.parent)
        obligation = data.get("obligation")
        if isinstance(obligation, str) and obligation:
            if obligation in seen:
                corpus.errors.append(
                    f"{path}: obligation '{obligation}' already has a spec at {seen[obligation]} — "
                    "merge duplicate L1/L2 specs into one spec per obligation"
                )
            else:
                seen[obligation] = path


def validate_check_spec(
    data: dict[str, Any],
    *,
    path: Path,
    errors: list[str],
    known_ids: set[str] | None = None,
    repo_root: Path | None = None,
) -> None:
    """Run every content check for one check-spec document.

    ``known_ids`` holds the corpus obligation ids; the ``obligation``
    membership check is skipped when it is empty or missing (an empty
    corpus cannot resolve refs). ``repo_root`` resolves ``fixtures``
    paths for ``L2`` specs (defaults to the directory above ``checks/``).
    """
    _validate_spec_identity(data, path, errors)
    _validate_spec_obligation(data, path, errors, known_ids or set())
    _validate_spec_level(data, path, errors)
    _validate_spec_triggers(data, path, errors)
    _validate_spec_gate(data, path, errors, repo_root or _default_repo_root(path))


def _validate_spec_identity(data: dict[str, Any], path: Path, errors: list[str]) -> None:
    spec_id = data.get("id")
    if not isinstance(spec_id, str) or not spec_id:
        errors.append(f"{path}: id must be a non-empty string, got {spec_id!r}")
        return
    expected = f"{path.parent.name}/{path.stem}"
    if spec_id != expected:
        errors.append(f"{path}: id '{spec_id}' does not match path '{expected}'")


def _validate_spec_obligation(data: dict[str, Any], path: Path, errors: list[str], known_ids: set[str]) -> None:
    obligation = data.get("obligation")
    if not isinstance(obligation, str) or not obligation:
        errors.append(f"{path}: obligation must be a non-empty string, got {obligation!r}")
        return
    if known_ids and obligation not in known_ids:
        errors.append(f"{path}: obligation '{obligation}' does not match any id in the corpus")


def _validate_spec_level(data: dict[str, Any], path: Path, errors: list[str]) -> None:
    level = data.get("level")
    if not isinstance(level, str) or level not in ENFORCEMENT_LEVELS:
        errors.append(f"{path}: level must be one of {sorted(ENFORCEMENT_LEVELS)}, got {level!r}")


def _validate_spec_triggers(data: dict[str, Any], path: Path, errors: list[str]) -> None:
    if "triggers" not in data:
        return
    triggers = data.get("triggers")
    if not isinstance(triggers, list):
        errors.append(f"{path}: triggers must be a list of regex strings, got {triggers!r}")
        return
    for index, pattern in enumerate(triggers):
        where = f"{path}: triggers[{index}]"
        if not isinstance(pattern, str) or not pattern.strip():
            errors.append(f"{where} must be a non-empty regex string, got {pattern!r}")
            continue
        try:
            re.compile(pattern)
        except re.error as exc:
            errors.append(f"{where} is not a valid regex: {exc}")


def _default_repo_root(path: Path) -> Path:
    """The directory above ``checks/`` for fixture resolution."""
    for parent in path.parents:
        if parent.name == "checks":
            return parent.parent
    return path.parent.parent


def _validate_spec_gate(data: dict[str, Any], path: Path, errors: list[str], repo_root: Path) -> None:
    """An ``L2`` hard gate is allowed only with an executable rule and fixtures that exist.

    ``blocking`` wires the gate into a release job (the executable rule);
    ``fixtures`` names repo-relative must-trigger / must-not-trigger files
    every one of which must exist. L0 prose and L1 detection specs carry
    no such requirement.
    """
    if data.get("level") != "L2":
        return
    blocking = data.get("blocking")
    if not isinstance(blocking, str) or not blocking.strip():
        errors.append(f"{path}: L2 specs need a 'blocking' rule wiring the gate into a release job")
    fixtures = data.get("fixtures")
    if not isinstance(fixtures, list) or not fixtures:
        errors.append(f"{path}: L2 specs need a non-empty 'fixtures' list of test files")
        return
    for fixture in fixtures:
        if not isinstance(fixture, str) or not fixture.strip():
            errors.append(f"{path}: fixtures must be repo-relative path strings, got {fixture!r}")
            continue
        target = Path(repo_root) / fixture.split("#")[0].strip()
        if not target.is_file():
            errors.append(f"{path}: fixture '{fixture}' does not exist under {repo_root}")
