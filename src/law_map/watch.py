"""law-watch: amendment feeds for the instruments the corpus cites.

``review_by`` dates catch staleness on a schedule; they miss a law that
changes before its review date (the EU AI Omnibus moved AI Act deadlines
months ahead of every ``review_by``). ``law-map watch`` asks each
instrument's official publisher whether it has been amended since a
grounding was last verified:

- EUR-Lex (CELEX, e.g. ``32024R1689``): Cellar SPARQL, acts recorded as
  amending the work (``cdm:resource_legal_amends_resource_legal``);
- e-Gov (law id, e.g. ``415AC0000000057``): API v2 ``law_revisions``, the
  latest ``amendment_promulgate_date``;
- legislation.gov.uk (``ukpga/1988/48``): the changes feed for the act,
  newest affecting legislation first.

A grounding's baseline is its ``reviewed_on`` date, else its ``effective``
date (a ``scheduled``/``proposed`` grounding has no baseline without
``reviewed_on``: its ``effective`` is a future date, not a verification).
An amendment newer than the baseline is reported as ``[law-watch changed]``;
re-verify the grounding and record ``reviewed_on`` to acknowledge it.
Instruments are fetched once each but compared per grounding. Never raises.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx

from .model import Corpus, obligation_groundings, parse_iso_date
from .sources import USER_AGENT

__all__ = [
    "Instrument",
    "WatchFetch",
    "WatchProbe",
    "collect_watch_refs",
    "format_watch_line",
    "format_watch_summary",
    "instruments_of",
    "latest_egov_amendment",
    "latest_eurlex_amendment",
    "latest_uk_effect",
    "watch_laws",
]

TIMEOUT = 30.0
EURLEX_SPARQL = "https://publications.europa.eu/webapi/rdf/sparql"
EGOV_REVISIONS = "https://laws.e-gov.go.jp/api/2/law_revisions/{id}"
UK_CHANGES_FEED = (
    "https://www.legislation.gov.uk/changes/affected/{id}/data.feed"
    "?results-count=20&sort=affecting-year-number&order=descending"
)
EURLEX_QUERY = """PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
SELECT ?celex ?date WHERE {{
  ?work cdm:resource_legal_id_celex "{celex}"^^<http://www.w3.org/2001/XMLSchema#string> .
  ?amending cdm:resource_legal_amends_resource_legal ?work .
  ?amending cdm:resource_legal_id_celex ?celex .
  OPTIONAL {{ ?amending cdm:work_date_document ?date . }}
}} ORDER BY DESC(?date) LIMIT 5"""
ATOM = "{http://www.w3.org/2005/Atom}"
UKM = "{http://www.legislation.gov.uk/namespaces/metadata}"

_ELI_RE = re.compile(r"eur-lex\.europa\.eu/eli/(reg|dir|dec)/(\d{4})/(\d+)/oj")
_ELI_LETTER = {"reg": "R", "dir": "L", "dec": "D"}
_CELEX_RE = re.compile(r"^3\d{4}[RLD]\d{4}$")
_EGOV_RE = re.compile(r"laws\.e-gov\.go\.jp/(?:document\?lawid=|law/)([0-9A-Za-z]+)")
_UK_RE = re.compile(r"legislation\.gov\.uk/((?:ukpga|uksi|asp|ssi|anaw|asc|wsi|nia|nisr|nisi)/\d{4}/\d+)")
_OPEN_LAW_KIND = {"eu": "eurlex", "jp": "egov", "uk": "uk", "gb": "uk"}
_NO_BASELINE_STATUSES = {"scheduled", "proposed"}


@dataclass(frozen=True)
class Instrument:
    kind: str  # "eurlex" | "egov" | "uk"
    ident: str  # CELEX | e-Gov law id | "<type>/<year>/<number>"

    def __str__(self) -> str:
        return f"{self.kind}:{self.ident}"


# Instrument -> (latest amendment date YYYY-MM-DD, what amended it), or None
# when the publisher records no amendment. Raise on network/parse failure.
WatchFetch = Callable[[Instrument], tuple[str, str] | None]


@dataclass
class WatchRef:
    obligation_id: str
    index: int
    instrument: Instrument
    baseline_field: str | None  # "reviewed_on" | "effective" | None
    baseline: str | None


@dataclass
class WatchProbe:
    ref: WatchRef
    latest: str | None
    detail: str | None
    problem: str | None  # "changed" | "not-found" | "unreachable" | None


def instruments_of(grounding: dict[str, Any]) -> list[Instrument]:
    """Watchable instruments a grounding cites, via its ``open_law`` ref and source URLs."""
    found: list[Instrument] = []
    ref = grounding.get("open_law")
    if isinstance(ref, dict) and isinstance(ref.get("id"), str):
        kind = _OPEN_LAW_KIND.get(str(ref.get("source")))
        if kind is not None:
            found.append(Instrument(kind, ref["id"]))
    for url in grounding.get("sources") or []:
        if not isinstance(url, str):
            continue
        if m := _ELI_RE.search(url):
            kind_letter = _ELI_LETTER[m.group(1)]
            found.append(Instrument("eurlex", f"3{m.group(2)}{kind_letter}{int(m.group(3)):04d}"))
        elif m := _EGOV_RE.search(url):
            found.append(Instrument("egov", m.group(1)))
        elif m := _UK_RE.search(url):
            found.append(Instrument("uk", m.group(1)))
    return list(dict.fromkeys(i for i in found if i.kind != "eurlex" or _CELEX_RE.match(i.ident)))


def collect_watch_refs(corpus: Corpus) -> list[WatchRef]:
    """One ref per (grounding, cited instrument), with the grounding's baseline date."""
    refs: list[WatchRef] = []
    for ob in corpus.obligations:
        for index, g in enumerate(obligation_groundings(ob)):
            field_name: str | None = None
            if parse_iso_date(g.get("reviewed_on")) is not None:
                field_name = "reviewed_on"
            elif g.get("status") not in _NO_BASELINE_STATUSES and parse_iso_date(g.get("effective")):
                field_name = "effective"
            baseline = str(g[field_name]) if field_name else None
            for instrument in instruments_of(g):
                refs.append(WatchRef(ob.id, index, instrument, field_name, baseline))
    return refs


def watch_laws(corpus: Corpus, fetch: WatchFetch | None = None) -> list[WatchProbe]:
    """Compare each cited instrument's latest amendment with its groundings' baselines.

    *fetch* injects the publisher lookup (tests, offline); without it the
    official feeds are queried over HTTPS.
    """
    if fetch is None:
        with httpx.Client(timeout=TIMEOUT, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
            return _watch(corpus, _http_fetch(client))
    return _watch(corpus, fetch)


def _watch(corpus: Corpus, fetch: WatchFetch) -> list[WatchProbe]:
    cache: dict[Instrument, tuple[str, str] | None | Exception] = {}
    probes: list[WatchProbe] = []
    for ref in collect_watch_refs(corpus):
        if ref.instrument not in cache:
            try:
                cache[ref.instrument] = fetch(ref.instrument)
            except Exception as exc:  # network, HTTP status, or payload shape
                cache[ref.instrument] = exc
        result = cache[ref.instrument]
        if isinstance(result, Exception):
            not_found = isinstance(result, httpx.HTTPStatusError) and result.response.status_code == 404
            probes.append(WatchProbe(ref, None, None, "not-found" if not_found else "unreachable"))
            continue
        latest, detail = result if result is not None else (None, None)
        changed = latest is not None and (ref.baseline is None or latest > ref.baseline)
        probes.append(WatchProbe(ref, latest, detail, "changed" if changed else None))
    return probes


def format_watch_line(p: WatchProbe) -> str | None:
    """One flagged line, or ``None`` when the grounding is current."""
    where = f"{p.ref.obligation_id} groundings[{p.ref.index}] {p.ref.instrument}"
    if p.problem == "not-found":
        return f"[law-watch not-found] {where}: the publisher has no such instrument (wrong id?)"
    if p.problem == "unreachable":
        return f"[law-watch unreachable] {where}"
    if p.problem != "changed":
        return None
    since = f"after {p.ref.baseline_field} {p.ref.baseline}" if p.ref.baseline else "no reviewed_on recorded"
    return f"[law-watch changed] {where}: amended {p.latest} by {p.detail} ({since})"


def format_watch_summary(probes: list[WatchProbe]) -> str:
    """``law-watch: N instrument(s), M grounding(s) changed, K not found, L unreachable``."""
    instruments = {p.ref.instrument for p in probes}
    changed = sum(1 for p in probes if p.problem == "changed")
    not_found = sum(1 for p in probes if p.problem == "not-found")
    unreachable = sum(1 for p in probes if p.problem == "unreachable")
    return (
        f"law-watch: {len(instruments)} instrument(s), {changed} grounding(s) changed, "
        f"{not_found} not found, {unreachable} unreachable"
    )


def latest_eurlex_amendment(payload: dict[str, Any]) -> tuple[str, str] | None:
    """Newest amending act from a Cellar SPARQL JSON result: (date, CELEX)."""
    best: tuple[str, str] | None = None
    for row in payload["results"]["bindings"]:
        date = row.get("date", {}).get("value")
        celex = row["celex"]["value"]
        if date and (best is None or date > best[0]):
            best = (date[:10], f"CELEX {celex}")
    return best


def latest_egov_amendment(payload: dict[str, Any]) -> tuple[str, str] | None:
    """Newest promulgated amendment from an e-Gov ``law_revisions`` response."""
    best: tuple[str, str] | None = None
    for rev in payload["revisions"]:
        date = rev.get("amendment_promulgate_date")
        if date and (best is None or date > best[0]):
            best = (date, rev.get("amendment_law_num") or rev.get("amendment_law_id") or "?")
    return best


def latest_uk_effect(feed: str) -> tuple[str, str] | None:
    """Most recently recorded effect from a legislation.gov.uk changes feed."""
    if "<!DOCTYPE" in feed:
        # The feed never declares a DTD; refusing one keeps entity expansion out.
        raise ValueError("unexpected DOCTYPE in legislation.gov.uk feed")
    root = ET.fromstring(feed)
    best: tuple[str, str] | None = None
    for entry in root.iter(f"{ATOM}entry"):
        updated = entry.findtext(f"{ATOM}updated")
        effect = entry.find(f".//{UKM}Effect")
        affecting = effect.get("AffectingURI", "?") if effect is not None else "?"
        if updated and (best is None or updated[:10] > best[0]):
            best = (updated[:10], affecting.removeprefix("http://www.legislation.gov.uk/id/"))
    return best


def _http_fetch(client: httpx.Client) -> WatchFetch:
    def _fetch(instrument: Instrument) -> tuple[str, str] | None:
        if instrument.kind == "eurlex":
            resp = client.get(
                EURLEX_SPARQL,
                params={
                    "query": EURLEX_QUERY.format(celex=instrument.ident),
                    "format": "application/sparql-results+json",
                },
            )
            resp.raise_for_status()
            return latest_eurlex_amendment(resp.json())
        if instrument.kind == "egov":
            resp = client.get(EGOV_REVISIONS.format(id=instrument.ident))
            resp.raise_for_status()
            return latest_egov_amendment(resp.json())
        resp = client.get(UK_CHANGES_FEED.format(id=instrument.ident))
        resp.raise_for_status()
        return latest_uk_effect(resp.text)

    return _fetch
