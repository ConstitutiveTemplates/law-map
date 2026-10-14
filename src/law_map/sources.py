"""Source-URL liveness probes for grounding ``sources``.

HEADs each distinct grounding URL (10s timeout, polite UA, no redirect
following) and flags 404s, redirects, and unreachable hosts. This is one
of the two network-touching parts of ``law-map check --sources``; the
other is :mod:`law_map.openlaw`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import httpx

from .model import Corpus, iter_groundings

TIMEOUT = 10.0
USER_AGENT = "law-map-check/0.1 (+https://github.com/politeuma/law-map)"


@dataclass
class SourceProbe:
    url: str
    status: int | None
    problem: str | None  # "not-found" | "redirect" | "unreachable" | None


def probe_sources(corpus: Corpus, extra_urls: list[str] | None = None) -> list[SourceProbe]:
    """HEAD each grounding source URL (plus ``extra_urls``); flag 404s, redirects, unreachable hosts."""
    probes: list[SourceProbe] = []
    seen: set[str] = set()
    with httpx.Client(timeout=TIMEOUT, follow_redirects=False, headers={"User-Agent": USER_AGENT}) as client:
        for g in iter_groundings(corpus):
            for url in g.get("sources", []):
                if not isinstance(url, str) or url in seen:
                    continue
                seen.add(url)
                probes.append(_probe_source_url(client, url))
        for url in extra_urls or []:
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


def guidance_section_urls(guidance_root: Path) -> list[str]:
    """Declared ``sources:`` URLs of every ``guidance/sections/<tier>/<slug>.md``.

    Offline front-matter read only (no network). Returns the deduped URLs in
    file order; returns [] when the guidance tree is absent (e.g. a bare
    obligations checkout).
    """
    return [url for _, urls, _ in guidance_section_refs(guidance_root) for url in urls]


def guidance_section_refs(guidance_root: Path) -> list[tuple[str, list[str], str | None]]:
    """``(section_id, sources, version_date)`` per guidance section file.

    ``section_id`` follows the ``<tier>-<slug>`` rule, ``version_date`` is the
    ``YYYY-MM-DD`` part of front matter ``version: "YYYY-MM-DD.rev"`` (None
    when unparseable). Skips unreadable files; returns [] when the guidance
    tree is absent.
    """
    import yaml

    sections = Path(guidance_root) / "sections"
    if not sections.is_dir():
        return []
    found: list[tuple[str, list[str], str | None]] = []
    seen_urls: set[str] = set()
    for path in sorted(sections.glob("*/*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if not text.startswith("---\n"):
            continue
        try:
            front = yaml.safe_load(text.split("---\n", 2)[1])
        except yaml.YAMLError:
            continue
        if not isinstance(front, dict):
            continue
        sid = front.get("id") or f"{path.parent.name}-{path.name.removesuffix('.md')}"
        urls: list[str] = []
        sources = front.get("sources")
        if isinstance(sources, list):
            for url in sources:
                if isinstance(url, str) and url.startswith(("http://", "https://")) and url not in seen_urls:
                    seen_urls.add(url)
                    urls.append(url)
        version = front.get("version")
        version_date = str(version).split(".", 0)[0] if isinstance(version, str) else None
        found.append((str(sid), urls, version_date))
    return found
