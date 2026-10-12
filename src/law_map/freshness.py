"""Review-freshness checks over grounding ``review_by`` dates.

Pure and offline: :func:`check_reviews` lists the groundings whose
``review_by`` date is within the horizon or already expired, sorted for
stable output.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from .model import Corpus, obligation_groundings, parse_iso_date

DEFAULT_DAYS = 30


@dataclass
class Expiry:
    obligation_id: str
    jurisdiction: str
    citation: str
    review_by: date
    expired: bool  # True when past review_by, else within horizon


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


def format_expiry_line(e: Expiry) -> str:
    """One review-freshness line for the ``check`` command output."""
    state = "EXPIRED" if e.expired else f"due by {e.review_by}"
    return f"[{state}] {e.obligation_id} ({e.jurisdiction}): {e.citation}"
