"""Source-URL liveness probes for grounding ``sources``.

HEADs each distinct grounding URL (10s timeout, polite UA, no redirect
following) and flags 404s, redirects, and unreachable hosts. This is one
of the two network-touching parts of ``law-map check --sources``; the
other is :mod:`law_map.openlaw`.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from .model import Corpus, iter_groundings

TIMEOUT = 10.0
USER_AGENT = "law-map-check/0.1 (+https://github.com/politeuma/law-map)"


@dataclass
class SourceProbe:
    url: str
    status: int | None
    problem: str | None  # "not-found" | "redirect" | "unreachable" | None


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
                probes.append(_probe_source_url(client, url))
    return probes


def _probe_source_url(client: httpx.Client, url: str) -> SourceProbe:
    try:
        resp = client.head(url)
    except httpx.HTTPError:
        return SourceProbe(url=url, status=None, problem="unreachable")
    if resp.status_code == 404:
        return SourceProbe(url=url, status=resp.status_code, problem="not-found")
    if resp.is_redirect or resp.status_code in (301, 302, 303, 307, 308):
        return SourceProbe(url=url, status=resp.status_code, problem="redirect")
    return SourceProbe(url=url, status=resp.status_code, problem=None)


def format_source_line(p: SourceProbe) -> str | None:
    """One flagged source line, or ``None`` when the probe is clean."""
    if p.problem is None:
        return None
    return f"[source {p.problem}] {p.url}"


def format_source_summary(probes: list[SourceProbe]) -> str:
    """``source probes: N total, M flagged`` summary line."""
    flagged = sum(1 for p in probes if p.problem is not None)
    return f"source probes: {len(probes)} total, {flagged} flagged"
