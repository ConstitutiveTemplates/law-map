"""Review-freshness reports over the obligation corpus.

``check`` reports groundings whose ``review_by`` date is within the horizon
or already expired (see :mod:`law_map.freshness`). With ``--sources`` it
additionally performs HEAD requests against every grounding source URL
(see :mod:`law_map.sources`) and resolves every grounding ``open_law`` ref
through open-law (see :mod:`law_map.openlaw`). Only this command touches
the network; the rest of the toolchain is deterministic and offline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .freshness import DEFAULT_DAYS, Expiry, check_reviews, format_expiry_line
from .model import Corpus
from .openlaw import (
    OpenLawFetch,
    OpenLawProbe,
    format_open_law_line,
    format_open_law_summary,
    probe_open_law,
)
from .sources import SourceProbe, format_source_line, format_source_summary, probe_sources

__all__ = [
    "DEFAULT_DAYS",
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


def today() -> date:
    """Current date; a seam so tests can pin 'today'."""
    return date.today()


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
