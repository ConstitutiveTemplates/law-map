"""open-law amendment probes for grounding ``open_law`` refs.

Resolves every grounding ``open_law`` ref (``{source, id}``) through
open-law's ``open_adapter(source).fetch(id)``: an upstream ``modified``
newer than the grounding's ``effective`` date is reported as amended,
with a sha256 of the fetched text for pinning. Refs are skipped when
open-law is not installed and reported as unavailable when the source
serves no machine full text. Never raises. This is one of the two
network-touching parts of ``law-map check --sources``; the other is
:mod:`law_map.sources`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from hashlib import sha256

from .model import Corpus, obligation_groundings, parse_iso_date

# (source, law_id) -> (upstream modified date, full text or None when the
# source serves metadata only). Inject fakes in tests; without one the ref
# resolves through open-law's open_adapter(source).fetch(id).
OpenLawFetch = Callable[[str, str], tuple[str | None, str | None]]


@dataclass
class OpenLawProbe:
    obligation_id: str
    source: str
    law_id: str
    modified: str | None
    content_sha256: str | None
    problem: str | None  # "amended" | "unavailable" | "unreachable" | "skipped" | None


def probe_open_law(corpus: Corpus, fetch: OpenLawFetch | None = None) -> list[OpenLawProbe]:
    """Resolve every grounding ``open_law`` ref via open-law and flag amendments.

    *fetch* injects ``(source, law_id) -> (modified, text)`` (tests, offline);
    without it the ref resolves through ``open_adapter(source).fetch(id)``.
    Refs deduplicate by ``(source, law_id)`` like URL probes. Problems:
    ``amended`` (upstream ``modified`` newer than grounding ``effective``),
    ``unavailable`` (unknown source or no machine full text), ``unreachable``
    (the fetch itself blew up), ``skipped`` (open-law is not installed).
    Never raises.
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
    if p.problem == "amended":
        return f"[open-law amended] {p.obligation_id} {p.source}:{p.law_id} (upstream modified {p.modified})"
    if p.problem in ("unavailable", "unreachable"):
        return f"[open-law {p.problem}] {p.obligation_id} {p.source}:{p.law_id}"
    if p.problem == "skipped":
        return f"[skipped] {p.obligation_id}: open-law {p.source}:{p.law_id} not probed (package not installed)"
    return None


def format_open_law_summary(probes: list[OpenLawProbe]) -> str:
    """``open-law probes: N total, M flagged, skipped: K`` summary line."""
    skipped = sum(1 for p in probes if p.problem == "skipped")
    flagged = sum(1 for p in probes if p.problem in ("amended", "unreachable"))
    return f"open-law probes: {len(probes)} total, {flagged} flagged, skipped: {skipped}"


def _collect_open_law_refs(corpus: Corpus) -> list[tuple[str, str, str, object]]:
    """(obligation_id, source, law_id, effective) for well-shaped open_law refs.

    Malformed refs are validation errors, not probes — skip them here so a
    half-broken corpus still gets every probe it can.
    """
    refs: list[tuple[str, str, str, object]] = []
    for ob in corpus.obligations:
        for g in obligation_groundings(ob):
            ref = g.get("open_law")
            if not isinstance(ref, dict):
                continue
            source = ref.get("source")
            law_id = ref.get("id")
            if isinstance(source, str) and source.strip() and isinstance(law_id, str) and law_id.strip():
                refs.append((ob.id, source, law_id, g.get("effective")))
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


def _probe_from_fetch_error(ob_id: str, source: str, law_id: str, exc: Exception) -> OpenLawProbe:
    """Map a fetch failure to its ``unavailable``/``unreachable``/``skipped`` probe."""
    if isinstance(exc, ImportError):
        return OpenLawProbe(ob_id, source, law_id, None, None, "skipped")
    if exc.__class__.__name__ == "NotAvailableBySourceError" or isinstance(exc, ValueError):
        return OpenLawProbe(ob_id, source, law_id, None, None, "unavailable")
    return OpenLawProbe(ob_id, source, law_id, None, None, "unreachable")


def _is_amended(modified: str | None, effective: object) -> bool:
    """True when upstream *modified* is newer than the grounding's *effective* date."""
    amended_on = parse_iso_date(modified) if modified else None
    effective_on = parse_iso_date(effective)
    return amended_on is not None and effective_on is not None and amended_on > effective_on


def _skipped_open_law_probes(refs: list[tuple[str, str, str, object]]) -> list[OpenLawProbe]:
    """One ``skipped`` probe per ref (open-law is not installed)."""
    return [
        OpenLawProbe(
            obligation_id=ob_id,
            source=source,
            law_id=law_id,
            modified=None,
            content_sha256=None,
            problem="skipped",
        )
        for ob_id, source, law_id, _effective in refs
    ]


def _resolve_open_law_refs(
    refs: list[tuple[str, str, str, object]], fetch: OpenLawFetch
) -> list[OpenLawProbe]:
    """Resolve refs (deduped by ``(source, law_id)``); never raises."""
    probes: list[OpenLawProbe] = []
    seen: set[tuple[str, str]] = set()
    for ob_id, source, law_id, effective in refs:
        if (source, law_id) in seen:
            continue
        seen.add((source, law_id))
        try:
            modified, text = fetch(source, law_id)
        except Exception as exc:
            probes.append(_probe_from_fetch_error(ob_id, source, law_id, exc))
            continue
        digest = sha256(text.encode("utf-8")).hexdigest() if text else None
        problem: str | None = "amended" if _is_amended(modified, effective) else None
        probes.append(OpenLawProbe(ob_id, source, law_id, modified, digest, problem))
    return probes
