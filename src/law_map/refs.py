"""Cross-file reference checks for the obligation corpus.

Single-file shape is validated at load time by :mod:`law_map.validate`;
this module checks links *between* files: ``requires``/``conflicts`` id
existence, ``enforcement.check_refs`` spec files, and ``related_sections``
codex linkage (via :mod:`law_map.codex`). Runs after
:func:`~law_map.loader.load_corpus` and appends to the corpus's
error/warning lists.
"""

from __future__ import annotations

from pathlib import Path

from .codex import check_codex_coverage, codex_section_path, unresolved_section_error
from .model import Corpus, Obligation


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
        _check_obligation_links(ob, known_ids, section_users, corpus, checks_root, codex_root)
    if codex_root is not None:
        corpus.warnings.extend(check_codex_coverage(corpus, codex_root))


def _count_section_users(corpus: Corpus) -> dict[str, int]:
    """How many obligations reference each ``related_sections`` id."""
    users: dict[str, int] = {}
    for ob in corpus.obligations:
        for section in ob.data.get("related_sections", []):
            if isinstance(section, str):
                users[section] = users.get(section, 0) + 1
    return users


def _check_obligation_links(
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
                    corpus.errors.append(unresolved_section_error(ob.id, section))
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
                if not _check_spec_exists(checks_root, ref):
                    corpus.errors.append(
                        f"{ob.id}: enforcement.check_refs '{ref}' does not match checks/{ref}.yml"
                    )


def _check_spec_exists(checks_root: Path, ref: str) -> bool:
    target = Path(checks_root) / f"{ref}.yml"
    return target.is_file()
