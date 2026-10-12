"""Review-freshness checking, source-URL liveness, and open-law amendment probes.

``check`` reports groundings whose ``review_by`` date is within the horizon
or already expired. With ``--sources`` it additionally performs HEAD
requests against every grounding source URL (httpx, 10s timeout, polite UA)
and flags 404s and redirects, and it resolves every grounding ``open_law``
ref (``{source, id}``) through open-law's ``open_adapter(source).fetch(id)``:
an upstream ``modified`` newer than the grounding's ``effective`` date is
reported as amended, with a sha256 of the fetched text for pinning. Refs are
skipped when open-law is not installed and reported as unavailable when the
source serves no machine full text. Only this command touches the network;
the rest of the toolchain is deterministic and offline.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, timedelta
from hashlib import sha256

import httpx

from .model import Corpus, iter_groundings, obligation_groundings, parse_iso_date

DEFAULT_DAYS = 30
TIMEOUT = 10.0
USER_AGENT = "law-map-check/0.1 (+https://github.com/ConstitutiveTemplates/law-map)"


@dataclass
class Expiry:
    obligation_id: str
    jurisdiction: str
    citation: str
    review_by: date
    expired: bool  # True when past review_by, else within horizon


@dataclass
class SourceProbe:
    url: str
    status: int | None
    problem: str | None  # "not-found" | "redirect" | "unreachable" | None


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


@dataclass
class CheckReport:
    expiry: list[Expiry]
    probes: list[SourceProbe] = field(default_factory=list)
    open_law: list[OpenLawProbe] = field(default_factory=list)

    @property
    def expired(self) -> list[Expiry]:
        return [e for e in self.expiry if e.expired]

    @property
    def due(self) -> list[Expiry]:
        return [e for e in self.expiry if not e.expired]


def format_expiry_line(e: Expiry) -> str:
    """One review-freshness line for the ``check`` command output."""
    state = "EXPIRED" if e.expired else f"due by {e.review_by}"
    return f"[{state}] {e.obligation_id} ({e.jurisdiction}): {e.citation}"


def format_source_line(p: SourceProbe) -> str | None:
    """One flagged source line, or ``None`` when the probe is clean."""
    if p.problem is None:
        return None
    return f"[source {p.problem}] {p.url}"


def format_open_law_line(p: OpenLawProbe) -> str | None:
    """One open-law probe line, or ``None`` for clean (unflagged) probes."""
    if p.problem == "amended":
        return f"[open-law amended] {p.obligation_id} {p.source}:{p.law_id} (upstream modified {p.modified})"
    if p.problem in ("unavailable", "unreachable"):
        return f"[open-law {p.problem}] {p.obligation_id} {p.source}:{p.law_id}"
    if p.problem == "skipped":
        return (
            f"[skipped] {p.obligation_id}: open-law {p.source}:{p.law_id}"
            " not probed (package not installed)"
        )
    return None


def format_source_summary(probes: list[SourceProbe]) -> str:
    """``source probes: N total, M flagged`` summary line."""
    flagged = sum(1 for p in probes if p.problem is not None)
    return f"source probes: {len(probes)} total, {flagged} flagged"


def format_open_law_summary(probes: list[OpenLawProbe]) -> str:
    """``open-law probes: N total, M flagged, skipped: K`` summary line."""
    skipped = sum(1 for p in probes if p.problem == "skipped")
    flagged = sum(1 for p in probes if p.problem in ("amended", "unreachable"))
    return f"open-law probes: {len(probes)} total, {flagged} flagged, skipped: {skipped}"


def today() -> date:
    """Current date; a seam so tests can pin 'today'."""
    return date.today()


def check_reviews(corpus: Corpus, today: date, days: int = DEFAULT_DAYS) -> list[Expiry]:
    """List groundings expiring within ``days`` of ``today`` or already expired."""
    results: list[Expiry] = []
    horizon = today + timedelta(days=days)
    for ob in corpus.obligations:
        for g in obligation_groundings(ob):
            review_by = parse_iso_date(g.get("review_by"))
            if review_by is None or review_by > horizon:
                continue
            results.append(
                Expiry(
                    obligation_id=ob.id,
                    jurisdiction=str(g.get("jurisdiction", "?")),
                    citation=str(g.get("citation", "?")),
                    review_by=review_by,
                    expired=review_by < today,
                )
            )
    results.sort(key=lambda e: (e.review_by, e.obligation_id))
    return results


def probe_sources(corpus: Corpus) -> list[SourceProbe]:
    """HEAD each grounding source URL; flag 404s, redirects, unreachable hosts."""
    probes: list[SourceProbe] = []
    seen: set[str] = set()
    with httpx.Client(timeout=TIMEOUT, follow_redirects=False, headers={"User-Agent": USER_AGENT}) as client:
        for g in iter_groundings(corpus):
            for url in g.get("sources", []):
                if not isinstance(url, str) or url in seen:
                    continue
                seen.add(url)
                probes.append(_probe(client, url))
    return probes


def _probe(client: httpx.Client, url: str) -> SourceProbe:
    try:
        resp = client.head(url)
    except httpx.HTTPError:
        return SourceProbe(url=url, status=None, problem="unreachable")
    if resp.status_code == 404:
        return SourceProbe(url=url, status=resp.status_code, problem="not-found")
    if resp.is_redirect or resp.status_code in (301, 302, 303, 307, 308):
        return SourceProbe(url=url, status=resp.status_code, problem="redirect")
    return SourceProbe(url=url, status=resp.status_code, problem=None)


def run_check(
    corpus: Corpus,
    today: date,
    days: int,
    sources: bool,
    open_law_fetch: OpenLawFetch | None = None,
) -> CheckReport:
    report = CheckReport(expiry=check_reviews(corpus, today, days))
    if sources:
        report.probes = probe_sources(corpus)
        report.open_law = probe_open_law(corpus, fetch=open_law_fetch)
    return report


def _iter_open_law_refs(corpus: Corpus) -> list[tuple[str, str, str, object]]:
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
    from open_law.sources import open_adapter  # type: ignore[import-not-found]

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


def _open_law_fetch_error_probe(
    ob_id: str, source: str, law_id: str, exc: Exception
) -> OpenLawProbe:
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


def _skipped_probes(refs: list[tuple[str, str, str, object]]) -> list[OpenLawProbe]:
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


def _probe_open_law_refs(
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
            probes.append(_open_law_fetch_error_probe(ob_id, source, law_id, exc))
            continue
        digest = sha256(text.encode("utf-8")).hexdigest() if text else None
        problem: str | None = "amended" if _is_amended(modified, effective) else None
        probes.append(OpenLawProbe(ob_id, source, law_id, modified, digest, problem))
    return probes


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
    refs = _iter_open_law_refs(corpus)
    if fetch is None:
        try:
            fetch = _default_open_law_fetch()
        except ImportError:
            return _skipped_probes(refs)
    return _probe_open_law_refs(refs, fetch)


__all__ = [
    "CheckReport",
    "Expiry",
    "OpenLawFetch",
    "OpenLawProbe",
    "SourceProbe",
    "check_reviews",
    "format_expiry_line",
    "format_open_law_line",
    "format_open_law_summary",
    "format_source_line",
    "format_source_summary",
    "probe_open_law",
    "probe_sources",
    "run_check",
    "today",
]
