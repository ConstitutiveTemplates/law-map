"""Source liveness check orchestration: probe, classify, print, drift."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from .const import (
    FLAGGED_STATUS_PREFIXES,
    NO_HTTP_STATUS_MARKER,
    REVIEW_HORIZON,
    SECTIONS,
    UNAVAILABLE_MARKER,
    ProbeFn,
    SourceFlag,
)
from .corpus import check_review_by, section_files
from .probe import probe_source
from .sources import collect_source_urls
from .upstream import check_upstream_project_status


def is_flagged_status(status: str, *, has_upstream_grounding: bool = False) -> bool:
    """Whether a probe result counts as a dead/flagged source."""
    if status == "403" and has_upstream_grounding:
        return False
    return (
        status.startswith(FLAGGED_STATUS_PREFIXES)
        or NO_HTTP_STATUS_MARKER in status
        or UNAVAILABLE_MARKER in status
    )


def format_source_summary(probed: int, flagged: int) -> str:
    return f"[drift] source probes: {probed} total, {flagged} flagged"


def print_source_summary(probed: int, flagged: int) -> None:
    if not probed:
        print("[drift] no source URLs declared (add sources: to section front matter)")
    else:
        print(format_source_summary(probed, flagged))
        if not flagged:
            print("[drift] all sources live")


def _probe_unique_urls(
    collected: dict[str, list[str]],
    probe: ProbeFn,
) -> tuple[dict[str, str], int]:
    """Probe each unique URL once in origin order; return (status by url, probed count)."""
    statuses: dict[str, str] = {}
    probed = 0
    for _origin, urls in collected.items():
        for url in urls:
            if url not in statuses:
                statuses[url] = probe(url)
                probed += 1
    return statuses, probed


def _is_flagged_with_grounding(origin: str, url: str, status: str) -> bool:
    """Flag classification that excuses 403s covered by an upstream grounding."""
    upstream = check_upstream_project_status(origin, url) if status == "403" else []
    return is_flagged_status(status, has_upstream_grounding=bool(upstream))


def check_sources(
    sections_dir: Path = SECTIONS,
    probe: ProbeFn = probe_source,
) -> tuple[int, list[SourceFlag]]:
    """Probe each unique declared URL once; return (probed, flagged origins)."""
    collected = collect_source_urls(sections_dir)
    statuses, probed = _probe_unique_urls(collected, probe)
    flagged: list[SourceFlag] = []
    for origin, urls in collected.items():
        for url in urls:
            status = statuses[url]
            if _is_flagged_with_grounding(origin, url, status):
                flagged.append((origin, url, status))
    return probed, flagged


def flagged_unique_count(flagged: list[SourceFlag]) -> int:
    return len({url for _, url, _ in flagged})


def _format_source_line(origin: str, url: str, status: str, *, flagged: bool) -> str:
    line = f"{origin}: {url} -> {status}"
    return f"{line}  <-- FLAGGED" if flagged else line


def _print_upstream_notes(origin: str, url: str) -> None:
    for note in check_upstream_project_status(origin, url):
        print(note)


def run_sources_check(
    sections_dir: Path = SECTIONS,
    probe: ProbeFn = probe_source,
) -> int:
    probed, flagged = check_sources(sections_dir, probe)
    for origin, url, status in flagged:
        print(_format_source_line(origin, url, status, flagged=True))
        _print_upstream_notes(origin, url)
    print_source_summary(probed, flagged_unique_count(flagged))
    return 1 if flagged else 0


def _report_review_dates_drift() -> None:
    print("[drift] due/expired review_by:")
    today = dt.datetime.now(dt.UTC).date()
    any_due = False
    for path in section_files():
        body = path.read_text(encoding="utf-8")
        dates = check_review_by(path, body, drift_mode=True)
        if any(d < today or d <= today + REVIEW_HORIZON for _, d in dates):
            any_due = True
    if not any_due:
        print("[drift] no review_by due or expired")


def _report_source_liveness() -> tuple[int, int]:
    print("\n[drift] source liveness (curl HEAD, GET fallback):")
    collected = collect_source_urls(SECTIONS)
    statuses, probed = _probe_unique_urls(collected, probe_source)
    flagged_urls: set[str] = set()
    for origin, urls in collected.items():
        for url in urls:
            status = statuses[url]
            bad = is_flagged_status(status)
            if bad:
                flagged_urls.add(url)
            print(_format_source_line(origin, url, status, flagged=bad))
            if bad:
                _print_upstream_notes(origin, url)
    return probed, len(flagged_urls)


def drift_report() -> tuple[int, int]:
    _report_review_dates_drift()
    return _report_source_liveness()
