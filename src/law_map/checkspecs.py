"""Loading and validation for ``checks/<domain>/<slug>.yml`` machine-check specs.

Obligation documents point at specs through ``enforcement.check_refs``
(existence of the target file is checked in :mod:`law_map.refs`); this
module validates spec *content*: the ``id``/``obligation``/``level``
shape, ``id`` matching the file path, ``level`` in the enforcement
vocabulary, the ``obligation`` ref resolving into the corpus, and every
``triggers`` entry compiling as a regex. Problems land in
``corpus.errors`` so ``law-map validate`` fails on them, and law-lint
consumes the same ``triggers`` field via ``--rules <checks-dir>``.
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
    known_ids = {ob.id for ob in corpus.obligations if ob.id}
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
        validate_check_spec(data, path=path, errors=corpus.errors, known_ids=known_ids)


def validate_check_spec(
    data: dict[str, Any],
    *,
    path: Path,
    errors: list[str],
    known_ids: set[str] | None = None,
) -> None:
    """Run every content check for one check-spec document.

    ``known_ids`` holds the corpus obligation ids; the ``obligation``
    membership check is skipped when it is empty or missing (an empty
    corpus cannot resolve refs).
    """
    _validate_spec_identity(data, path, errors)
    _validate_spec_obligation(data, path, errors, known_ids or set())
    _validate_spec_level(data, path, errors)
    _validate_spec_triggers(data, path, errors)


def _validate_spec_identity(data: dict[str, Any], path: Path, errors: list[str]) -> None:
    spec_id = data.get("id")
    if not isinstance(spec_id, str) or not spec_id:
        errors.append(f"{path}: id must be a non-empty string, got {spec_id!r}")
        return
    expected = f"{path.parent.name}/{path.stem}"
    if spec_id != expected:
        errors.append(f"{path}: id '{spec_id}' does not match path '{expected}'")


def _validate_spec_obligation(
    data: dict[str, Any], path: Path, errors: list[str], known_ids: set[str]
) -> None:
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
