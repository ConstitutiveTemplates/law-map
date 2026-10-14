"""Guidance section linkage (``guidance/sections/``).

``related_sections`` ids follow the ``<tier>-<slug>`` rule:
``baseline-personal-data`` resolves to
``guidance/sections/baseline/personal-data.md`` inside this repo.
The forward check (:func:`check_codex_sections`) errors on ids that
resolve nowhere; the reverse check (:func:`check_codex_coverage`) warns
about guidance sections no obligation references.
"""

from __future__ import annotations

from pathlib import Path

from .model import Corpus

GUIDANCE_SECTIONS_DIR = Path("guidance") / "sections"
CODEX_SECTIONS_DIR = "sections"


def codex_section_path(codex_root: Path, section_id: str) -> Path | None:
    """Map a ``related_sections`` id to its guidance section file.

    ``baseline-personal-data`` resolves to
    ``guidance/sections/baseline/personal-data.md``: the id's first segment is
    the tier directory, the rest the slug. ``codex_root`` accepts the repo
    root (merged ``guidance/`` tree) or a bare sections checkout; ids like
    ``personal-data`` (``personal`` is not a tier) resolve to None, as do ids
    with no separator or an empty slug.
    """
    tier, sep, slug = section_id.partition("-")
    if not sep or not tier or not slug:
        return None
    root = Path(codex_root)
    candidates = [root / GUIDANCE_SECTIONS_DIR / tier, root / CODEX_SECTIONS_DIR / tier]
    for tier_dir in candidates:
        if not tier_dir.is_dir():
            continue
        for suffix in (".md", ".md.jinja"):
            candidate = tier_dir / f"{slug}{suffix}"
            if candidate.is_file():
                return candidate
    return None


def unresolved_section_error(ob_id: str, section: str) -> str:
    """Shared wording for a ``related_sections`` id that resolves nowhere."""
    return (
        f"{ob_id}: related_sections '{section}' does not resolve to a "
        "guidance section (expected guidance/sections/<tier>/<slug>.md, "
        "e.g. baseline-personal-data -> guidance/sections/baseline/personal-data.md)"
    )


def check_codex_sections(corpus: Corpus, codex_root: Path) -> list[str]:
    """Verify every ``related_sections`` id resolves to a guidance section file.

    Per the ``<tier>-<slug>`` naming rule each id must map to an *existing*
    ``guidance/sections/<tier>/<slug>.md`` in this repo; anything else
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
                errors.append(unresolved_section_error(ob.id, section))
    return errors


def check_codex_coverage(corpus: Corpus, codex_root: Path) -> list[str]:
    """Warn for guidance sections that no obligation references (reverse coverage).

    Enumerates ``guidance/sections/<tier>/<slug>.md`` per the ``<tier>-<slug>``
    naming rule and reports every id absent from all obligations'
    ``related_sections``. Warnings only, never errors: the guidance set is
    legitimately broader than the obligation graph. Never raises — a
    missing checkout yields no warnings (the forward check reports errors).
    """
    referenced: set[str] = set()
    for ob in corpus.all_obligations:
        related = ob.data.get("related_sections", [])
        if isinstance(related, list):
            for section in related:
                if isinstance(section, str):
                    referenced.add(section)
    warnings: list[str] = []
    root = Path(codex_root)
    sections = root / GUIDANCE_SECTIONS_DIR
    if not sections.is_dir():
        sections = root / CODEX_SECTIONS_DIR
    if not sections.is_dir():
        return warnings
    for tier_dir in sorted(p for p in sections.iterdir() if p.is_dir()):
        for path in sorted(tier_dir.glob("*.md")):
            if path.name.startswith("_") or path.name.endswith(".jinja"):
                continue
            section_id = f"{tier_dir.name}-{path.name.removesuffix('.md')}"
            if section_id not in referenced:
                warnings.append(
                    f"codex section '{section_id}' has no referencing obligation "
                    "(no related_sections points at it)"
                )
    return warnings
