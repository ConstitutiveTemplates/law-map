"""Review-freshness checking and optional source-URL liveness probes.

``check`` reports groundings whose ``review_by`` date is within the horizon
or already expired. With ``--sources`` it additionally performs HEAD
requests against every grounding source URL (httpx, 10s timeout, polite UA)
and flags 404s and redirects. Only this command touches the network; the
rest of the toolchain is deterministic and offline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import httpx

from .model import Corpus

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


@dataclass
class CheckReport:
    expiry: list[Expiry]
    probes: list[SourceProbe] = field(default_factory=list)

    @property
    def expired(self) -> list[Expiry]:
        return [e for e in self.expiry if e.expired]

    @property
    def due(self) -> list[Expiry]:
        return [e for e in self.expiry if not e.expired]


def _parse_review_by(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def today() -> date:
    """Current date; a seam so tests can pin 'today'."""
    return date.today()


def check_reviews(corpus: Corpus, today: date, days: int = DEFAULT_DAYS) -> list[Expiry]:
    """List groundings expiring within ``days`` of ``today`` or already expired."""
    results: list[Expiry] = []
    horizon = today + timedelta(days=days)
    for ob in corpus.obligations:
        for g in ob.data.get("groundings", []):
            if not isinstance(g, dict):
                continue
            review_by = _parse_review_by(g.get("review_by"))
            if review_by is None:
                continue
            if review_by <= horizon:
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
        for g in _all_groundings(corpus):
            for url in g.get("sources", []):
                if not isinstance(url, str) or url in seen:
                    continue
                seen.add(url)
                probes.append(_probe(client, url))
    return probes


def _all_groundings(corpus: Corpus) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ob in corpus.obligations:
        for g in ob.data.get("groundings", []):
            if isinstance(g, dict):
                out.append(g)
    return out


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


def run_check(corpus: Corpus, today: date, days: int, sources: bool) -> CheckReport:
    report = CheckReport(expiry=check_reviews(corpus, today, days))
    if sources:
        report.probes = probe_sources(corpus)
    return report