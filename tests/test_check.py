"""Review-expiry logic with a fixed 'today'."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from law_map.check import CheckReport, check_reviews, run_check
from law_map.model import load_corpus

from .test_model import VALID_OBLIGATION


def make_corpus(tmp_path: Path, review_by: str) -> Path:
    doc = yaml.safe_load(yaml.safe_dump(VALID_OBLIGATION))
    doc["groundings"][0]["review_by"] = review_by
    root = tmp_path / "obligations"
    root.mkdir()
    (root / "ob0.yml").write_text(yaml.safe_dump(doc), encoding="utf-8")
    return root


def test_expired_grounding_reported(tmp_path: Path, monkeypatch) -> None:
    root = make_corpus(tmp_path, "2024-01-01")
    corpus = load_corpus(root)
    expiry = check_reviews(corpus, today=date(2026, 10, 4))
    assert len(expiry) == 1
    assert expiry[0].expired is True
    assert expiry[0].obligation_id == "obligation.privacy.valid-fixture"


def test_due_within_horizon_reported_not_expired(tmp_path: Path, monkeypatch) -> None:
    root = make_corpus(tmp_path, "2026-10-20")
    corpus = load_corpus(root)
    expiry = check_reviews(corpus, today=date(2026, 10, 4), days=30)
    assert len(expiry) == 1
    assert expiry[0].expired is False


def test_beyond_horizon_not_reported(tmp_path: Path, monkeypatch) -> None:
    root = make_corpus(tmp_path, "2030-01-01")
    corpus = load_corpus(root)
    expiry = check_reviews(corpus, today=date(2026, 10, 4), days=30)
    assert expiry == []


def test_boundary_exactly_at_horizon_is_due(tmp_path: Path, monkeypatch) -> None:
    root = make_corpus(tmp_path, "2026-11-03")
    corpus = load_corpus(root)
    expiry = check_reviews(corpus, today=date(2026, 10, 4), days=30)
    assert len(expiry) == 1


def test_run_check_offline(tmp_path: Path, monkeypatch) -> None:
    root = make_corpus(tmp_path, "2024-01-01")
    corpus = load_corpus(root)
    report = run_check(corpus, today=date(2026, 10, 4), days=30, sources=False)
    assert isinstance(report, CheckReport)
    assert len(report.expired) == 1
    assert report.probes == []


def test_sort_order_stable(tmp_path: Path, monkeypatch) -> None:
    root = make_corpus(tmp_path, "2026-10-20")
    corpus = load_corpus(root)
    expiry = check_reviews(corpus, today=date(2026, 10, 4), days=30)
    assert expiry == sorted(expiry, key=lambda e: (e.review_by, e.obligation_id))