"""Upstream grounding lookup: correlate failed URLs with law-map / open-law."""

from __future__ import annotations

from pathlib import Path

import yaml

from .const import (
    OBLIGATIONS_SUBDIR,
    OPEN_LAW_SOURCES_SUBDIR,
    REPO,
)


def _load_obligation_doc(path: Path) -> dict | None:
    try:
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _open_law_note(grounding: dict, open_law_dir: Path) -> str | None:
    ref = grounding.get("open_law")
    if not isinstance(ref, dict) or not open_law_dir.is_dir():
        return None
    src_id = ref.get("source")
    law_id = ref.get("id")
    adapter = open_law_dir / OPEN_LAW_SOURCES_SUBDIR / f"{src_id}.py"
    available = "adapter installed" if adapter.is_file() else "no local adapter"
    return f"       -> [open-law] source={src_id} law_id={law_id} ({available})"


def _obligation_notes(
    data: dict,
    *,
    ob_id: str,
    sec_id: str,
    url: str,
    open_law_dir: Path,
) -> list[str]:
    notes: list[str] = []
    related = data.get("related_sections", [])
    groundings = data.get("groundings", [])
    matched = False
    for grounding in groundings:
        if isinstance(grounding, dict) and url in grounding.get("sources", []):
            matched = True
            authority = str(grounding.get("authority", "unnamed authority")).strip()
            notes.append(
                f"    -> [law-map] {ob_id}: {authority} "
                f"(status: {grounding.get('status')}, review_by: {grounding.get('review_by')})"
            )
            open_law_note = _open_law_note(grounding, open_law_dir)
            if open_law_note is not None:
                notes.append(open_law_note)
    if not matched and sec_id in related:
        notes.append(
            f"    -> [law-map] governing obligation: {ob_id} ({data.get('title', '').strip()})"
        )
    return notes


def check_upstream_project_status(
    origin: str,
    url: str,
    law_map_dir: Path = REPO.parent,
    open_law_dir: Path = REPO.parent.parent / "open-law",
) -> list[str]:
    """Inspect upstream law-map and open-law for groundings covering a failed URL."""
    notes: list[str] = []
    if not law_map_dir.is_dir():
        return notes
    sec_id = origin.removesuffix(".md").replace("/", "-")
    for path in sorted((law_map_dir / OBLIGATIONS_SUBDIR).rglob("*.yml")):
        if path.name.startswith("_"):
            continue
        data = _load_obligation_doc(path)
        if data is None:
            continue
        ob_id = data.get("id") or path.stem
        notes.extend(_obligation_notes(data, ob_id=ob_id, sec_id=sec_id,
                                       url=url, open_law_dir=open_law_dir))
    return notes


def obligation_ids(law_map_dir: Path = REPO.parent) -> set[str] | None:
    """Every law-map obligation id (``obligations/<domain>/<slug>.yml``).

    None when no obligations tree is found (offline use without the merged
    repo around skips the unknown-id check instead of failing it).
    """
    root = law_map_dir / OBLIGATIONS_SUBDIR
    if not root.is_dir():
        return None
    known: set[str] = set()
    for path in sorted(root.rglob("*.yml")):
        if path.name.startswith("_"):
            continue
        data = _load_obligation_doc(path)
        if data is None:
            continue
        ob_id = data.get("id") or path.stem
        known.add(str(ob_id))
    return known


def obligation_sections(law_map_dir: Path = REPO.parent) -> dict[str, set[str]] | None:
    """Section id -> law-map obligation ids that list it in ``related_sections``.

    ``law_map_dir`` defaults to this repo's root (merged rulebook: obligations
    live at ``<root>/obligations/``). None when no obligations tree is found.
    """
    root = law_map_dir / OBLIGATIONS_SUBDIR
    if not root.is_dir():
        return None
    links: dict[str, set[str]] = {}
    for path in sorted(root.rglob("*.yml")):
        if path.name.startswith("_"):
            continue
        data = _load_obligation_doc(path)
        if data is None:
            continue
        ob_id = str(data.get("id") or path.stem)
        for sec_id in data.get("related_sections", []) or []:
            links.setdefault(str(sec_id), set()).add(ob_id)
    return links
