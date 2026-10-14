"""open-law amendment probes for grounding ``open_law`` refs.

Resolves every grounding ``open_law`` ref (``{source, id}``) through
open-law's ``open_adapter(source).fetch(id)``: an upstream ``modified``
newer than the grounding's ``effective`` date is reported as amended, and
a fetched text whose sha256 differs from the grounding's recorded
``verified_text_sha256`` is reported as changed. Fetches deduplicate by
``(source, law_id)`` but every grounding of the same law gets its own
probe (baseline dates and hashes differ per grounding). Refs are skipped
when open-law is not installed and reported as unavailable when the
source serves no machine full text. Never raises. This is one of the two
network-touching parts of ``law-map check --sources``; the other is
:mod:`law_map.sources`.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from .model import Corpus, obligation_groundings, parse_iso_date

# (source, law_id) -> (upstream modified date, full text or None when the
# source serves metadata only). Inject fakes in tests; without one the ref
# resolves through open-law's open_adapter(source).fetch(id).
OpenLawFetch = Callable[[str, str], tuple[str | None, str | None]]

# A YAML sequence item opening a mapping (`- jurisdiction: JP`). Source URL
# items (`- https://…`) never match: no space follows their colon.
_ITEM_RE = re.compile(r"- [A-Za-z0-9_-]+:(\s|$)")


@dataclass
class OpenLawProbe:
    obligation_id: str
    source: str
    law_id: str
    grounding_index: int
    modified: str | None
    content_sha256: str | None
    problem: str | None  # "amended" | "changed" | "unavailable" | "unreachable" | "skipped" | None


def probe_open_law(corpus: Corpus, fetch: OpenLawFetch | None = None) -> list[OpenLawProbe]:
    """Resolve every grounding ``open_law`` ref via open-law and flag amendments.

    *fetch* injects ``(source, law_id) -> (modified, text)`` (tests, offline);
    without it the ref resolves through ``open_adapter(source).fetch(id)``.
    Only fetching deduplicates by ``(source, law_id)``: one probe is
    returned per grounding so each grounding's ``effective`` baseline and
    recorded ``verified_text_sha256`` is compared. Problems: ``amended``
    (upstream ``modified`` newer than grounding ``effective``), ``changed``
    (fetched text differs from ``verified_text_sha256``), ``unavailable``
    (unknown source or no machine full text), ``unreachable`` (the fetch
    itself blew up), ``skipped`` (open-law is not installed). Never raises.
    """
    refs = _collect_open_law_refs(corpus)
    if fetch is None:
        try:
            fetch = _default_open_law_fetch()
        except ImportError:
            return _skipped_open_law_probes(refs)
    return _resolve_open_law_refs(refs, fetch)


def format_open_law_line(p: OpenLawProbe) -> str | None:
    """One open-law probe line, or ``None`` for clean (unflagged) probes."""
    where = f"{p.obligation_id} groundings[{p.grounding_index}] {p.source}:{p.law_id}"
    if p.problem == "amended":
        return f"[open-law amended] {where} (upstream modified {p.modified})"
    if p.problem == "changed":
        return f"[open-law changed] {where} (fetched text differs from verified_text_sha256)"
    if p.problem in ("unavailable", "unreachable"):
        return f"[open-law {p.problem}] {where}"
    if p.problem == "skipped":
        return f"[skipped] {p.obligation_id}: open-law {p.source}:{p.law_id} not probed (package not installed)"
    return None


def format_open_law_summary(probes: list[OpenLawProbe]) -> str:
    """``open-law probes: N total, M flagged, skipped: K`` summary line."""
    skipped = sum(1 for p in probes if p.problem == "skipped")
    flagged = sum(1 for p in probes if p.problem in ("amended", "changed", "unreachable"))
    return f"open-law probes: {len(probes)} total, {flagged} flagged, skipped: {skipped}"


# A collected ref: obligation id, grounding index, source, law id, and the
# grounding's comparison baselines (effective date, recorded text hash).
OpenLawRef = tuple[str, int, str, str, object, object]


def _collect_open_law_refs(corpus: Corpus) -> list[OpenLawRef]:
    """One ref per grounding ``open_law`` mapping, in obligation order.

    Malformed refs are validation errors, not probes — skip them here so a
    half-broken corpus still gets every probe it can.
    """
    refs: list[OpenLawRef] = []
    for ob in corpus.obligations:
        for index, g in enumerate(obligation_groundings(ob)):
            ref = g.get("open_law")
            if not isinstance(ref, dict):
                continue
            source = ref.get("source")
            law_id = ref.get("id")
            if isinstance(source, str) and source.strip() and isinstance(law_id, str) and law_id.strip():
                refs.append((ob.id, index, source, law_id, g.get("effective"), g.get("verified_text_sha256")))
    return refs


def _default_open_law_fetch() -> OpenLawFetch:
    """Build the real fetcher from open-law's registry.

    Imported lazily so law-map works without open-law installed (callers get
    ``skipped`` probes instead). Raises ImportError when it is missing.
    """
    from open_law.sources import open_adapter

    def _fetch(source: str, law_id: str) -> tuple[str | None, str | None]:
        adapter = open_adapter(source)
        law = adapter.fetch(law_id)
        modified: str | None = law.modified
        try:
            text: str | None = adapter.full_text(law_id)
        except Exception:
            # Metadata-only sources (e.g. JP e-Gov's gated full text): the
            # modified date still detects amendments without the body.
            text = None
        return modified, text

    return _fetch


def _probe_from_fetch_error(ob_id: str, index: int, source: str, law_id: str, exc: Exception) -> OpenLawProbe:
    """Map a fetch failure to its ``unavailable``/``unreachable``/``skipped`` probe."""
    if isinstance(exc, ImportError):
        return OpenLawProbe(ob_id, source, law_id, index, None, None, "skipped")
    if exc.__class__.__name__ == "NotAvailableBySourceError" or isinstance(exc, ValueError):
        return OpenLawProbe(ob_id, source, law_id, index, None, None, "unavailable")
    return OpenLawProbe(ob_id, source, law_id, index, None, None, "unreachable")


def _is_amended(modified: str | None, effective: object) -> bool:
    """True when upstream *modified* is newer than the grounding's *effective* date."""
    amended_on = parse_iso_date(modified) if modified else None
    effective_on = parse_iso_date(effective)
    return amended_on is not None and effective_on is not None and amended_on > effective_on


def _is_changed(text: str | None, verified: object) -> bool:
    """True when the fetched text hashes differently from the recorded ``verified_text_sha256``."""
    if text is None or not isinstance(verified, str) or not verified.strip():
        return False
    return sha256(text.encode("utf-8")).hexdigest() != verified


def _skipped_open_law_probes(refs: list[OpenLawRef]) -> list[OpenLawProbe]:
    """One ``skipped`` probe per ref (open-law is not installed)."""
    return [
        OpenLawProbe(
            obligation_id=ob_id,
            source=source,
            law_id=law_id,
            grounding_index=index,
            modified=None,
            content_sha256=None,
            problem="skipped",
        )
        for ob_id, index, source, law_id, _effective, _verified in refs
    ]


def _resolve_open_law_refs(refs: list[OpenLawRef], fetch: OpenLawFetch) -> list[OpenLawProbe]:
    """Fetch once per ``(source, law_id)``; compare every grounding; never raises."""
    fetched: dict[tuple[str, str], tuple[str | None, str | None] | Exception] = {}
    for _ob_id, _index, source, law_id, _effective, _verified in refs:
        if (source, law_id) in fetched:
            continue
        try:
            fetched[(source, law_id)] = fetch(source, law_id)
        except Exception as exc:
            fetched[(source, law_id)] = exc
    probes: list[OpenLawProbe] = []
    for ob_id, index, source, law_id, effective, verified in refs:
        result = fetched[(source, law_id)]
        if isinstance(result, Exception):
            probes.append(_probe_from_fetch_error(ob_id, index, source, law_id, result))
            continue
        modified, text = result
        digest = sha256(text.encode("utf-8")).hexdigest() if text else None
        if _is_changed(text, verified):
            problem: str | None = "changed"
        elif _is_amended(modified, effective):
            problem = "amended"
        else:
            problem = None
        probes.append(OpenLawProbe(ob_id, source, law_id, index, modified, digest, problem))
    return probes


@dataclass
class HashUpdate:
    path: object  # Path to the obligation file
    grounding_index: int
    sha256: str


def collect_hash_updates(corpus: Corpus, fetch: OpenLawFetch) -> list[HashUpdate]:
    """Fetch every grounding ``open_law`` ref and plan ``verified_text_sha256`` updates.

    Fetching deduplicates by ``(source, law_id)``; one update is planned
    per grounding whose text fetched successfully. Never raises — a failed
    fetch simply yields no update for its groundings.
    """
    refs = _collect_open_law_refs(corpus)
    updates: list[HashUpdate] = []
    paths: dict[tuple[str, int], object] = {}
    for ob in corpus.obligations:
        for index, _g in enumerate(obligation_groundings(ob)):
            paths.setdefault((ob.id, index), ob.path)
    fetched: dict[tuple[str, str], str | None] = {}
    for _ob_id, _index, source, law_id, _effective, _verified in refs:
        if (source, law_id) in fetched:
            continue
        try:
            _modified, text = fetch(source, law_id)
        except Exception:
            text = None
        fetched[(source, law_id)] = sha256(text.encode("utf-8")).hexdigest() if text else None
    for ob_id, index, source, law_id, _effective, _verified in refs:
        digest = fetched[(source, law_id)]
        if digest is not None and (ob_id, index) in paths:
            updates.append(HashUpdate(paths[(ob_id, index)], index, digest))
    return updates


def apply_hash_updates(updates: list[HashUpdate]) -> dict[str, int]:
    """Patch ``verified_text_sha256`` lines into obligation files, preserving the rest.

    The updater is line-based (PyYAML would drop comments): within each
    grounding's span it replaces an existing ``verified_text_sha256`` line
    or inserts one after the ``open_law`` block. Returns ``{str(path):
    updated_count}``. Raises ValueError when a target block is not found.
    """
    by_file: dict[object, list[HashUpdate]] = {}
    for update in updates:
        by_file.setdefault(update.path, []).append(update)
    counts: dict[str, int] = {}
    for path, file_updates in by_file.items():
        lines = Path(str(path)).read_text(encoding="utf-8").splitlines()
        for update in file_updates:
            lines = _patch_grounding_hash(lines, update.grounding_index, update.sha256)
        Path(str(path)).write_text("\n".join(lines) + "\n", encoding="utf-8")
        counts[str(path)] = len(file_updates)
    return counts


def _grounding_spans(lines: list[str]) -> list[tuple[int, int, str]]:
    """(start, end, key-indent) of each ``- <key>:`` grounding item, at any indent."""
    starts: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        stripped = line.lstrip(" ")
        # A mapping key (`- jurisdiction: JP`); source URLs (`- https://…`)
        # have no space after the colon and must not match.
        if _ITEM_RE.match(stripped):
            indent = line[: len(line) - len(stripped)]
            starts.append((i, indent + "  "))
    return [
        (start, starts[k + 1][0] if k + 1 < len(starts) else len(lines), key_indent)
        for k, (start, key_indent) in enumerate(starts)
    ]


def _patch_grounding_hash(lines: list[str], grounding_index: int, digest: str) -> list[str]:
    """Insert or replace the ``verified_text_sha256`` line of one grounding."""
    spans = _grounding_spans(lines)
    if grounding_index >= len(spans):
        raise ValueError(f"grounding #{grounding_index}: no such grounding item in file")
    start, end, key_indent = spans[grounding_index]
    child_indent = key_indent + "  "
    replacement = f'{key_indent}verified_text_sha256: "{digest}"'
    open_block = f"{key_indent}open_law:"
    for i in range(start, end):
        if lines[i].startswith(f"{key_indent}verified_text_sha256:"):
            lines[i] = replacement
            return lines
    for i in range(start, end):
        if lines[i] == open_block:
            insert_at = i + 1
            while insert_at < end and lines[insert_at].startswith(child_indent):
                insert_at += 1
            lines.insert(insert_at, replacement)
            return lines
        if lines[i].startswith(f"{open_block} {{"):
            # Inline flow mapping (e.g. PyYAML dumps): the hash goes on the next line.
            lines.insert(i + 1, replacement)
            return lines
    raise ValueError(f"grounding #{grounding_index}: no open_law block to attach verified_text_sha256 to")
