"""Review-expiry logic with a fixed 'today'."""

from __future__ import annotations

from datetime import date
from hashlib import sha256
from pathlib import Path

import yaml

from law_map import check as check_mod
from law_map.check import CheckReport, check_reviews, probe_open_law, run_check
from law_map.loader import load_corpus

from .test_model import VALID_OBLIGATION, write_corpus


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


def _open_law_doc() -> dict:
    """VALID_OBLIGATION with its grounding carrying an eu open_law ref."""
    doc = yaml.safe_load(yaml.safe_dump(VALID_OBLIGATION))
    grounding = doc["groundings"][0]
    grounding["effective"] = "2022-01-01"
    grounding["open_law"] = {"source": "eu", "id": "32016R0679"}
    return doc


def test_probe_open_law_flags_amended(tmp_path: Path) -> None:
    root = write_corpus(tmp_path, _open_law_doc())
    corpus = load_corpus(root)

    def fake(source: str, law_id: str) -> tuple[str | None, str | None]:
        assert (source, law_id) == ("eu", "32016R0679")
        return ("2024-03-01", "consolidated text v2")

    probes = probe_open_law(corpus, fetch=fake)
    assert len(probes) == 1
    probe = probes[0]
    assert probe.problem == "amended"
    assert probe.modified == "2024-03-01"
    assert probe.content_sha256 == sha256(b"consolidated text v2").hexdigest()


def test_probe_open_law_ok_when_upstream_not_newer(tmp_path: Path) -> None:
    root = write_corpus(tmp_path, _open_law_doc())
    corpus = load_corpus(root)
    probes = probe_open_law(corpus, fetch=lambda _s, _i: ("2022-01-01", "same text"))
    assert len(probes) == 1
    assert probes[0].problem is None
    assert probes[0].content_sha256 == sha256(b"same text").hexdigest()


def test_probe_open_law_skipped_when_fetch_raises_import_error(tmp_path: Path) -> None:
    root = write_corpus(tmp_path, _open_law_doc())
    corpus = load_corpus(root)

    def missing(_s: str, _i: str) -> tuple[str | None, str | None]:
        raise ImportError("No module named 'open_law'")

    probes = probe_open_law(corpus, fetch=missing)
    assert len(probes) == 1
    assert probes[0].problem == "skipped"
    assert probes[0].modified is None
    assert probes[0].content_sha256 is None


def test_probe_open_law_unavailable_and_unreachable(tmp_path: Path) -> None:
    doc = _open_law_doc()
    base = dict(doc["groundings"][0])
    gated = dict(base, open_law={"source": "xx", "id": "whatever"})
    broken = dict(base, open_law={"source": "eu", "id": "broken-id"})
    doc["groundings"].extend([gated, broken])
    root = write_corpus(tmp_path, doc)
    corpus = load_corpus(root)

    def fake(source: str, law_id: str) -> tuple[str | None, str | None]:
        if law_id == "32016R0679":
            return ("2022-01-01", "text")
        if source == "xx":
            raise ValueError("unknown source 'xx'")
        raise RuntimeError("connection reset")

    by_id = {p.law_id: p for p in probe_open_law(corpus, fetch=fake)}
    assert by_id["32016R0679"].problem is None
    assert by_id["whatever"].problem == "unavailable"
    assert by_id["broken-id"].problem == "unreachable"


def test_probe_open_law_fetches_once_but_probes_every_grounding(tmp_path: Path) -> None:
    doc = _open_law_doc()
    doc["groundings"].append(dict(doc["groundings"][0]))  # same (source, id): fetch once, probe twice
    doc["groundings"].append(
        {
            "jurisdiction": "JP",
            "source_type": "statute",
            "status": "in_force",
            "authority": "Z",
            "citation": "W",
            "review_by": "2027-01-01",
            "sources": ["https://example.com/"],
            "open_law": "not-a-mapping",
        }
    )
    root = write_corpus(tmp_path, doc)
    corpus = load_corpus(root)
    calls: list[tuple[str, str]] = []

    def fake(source: str, law_id: str) -> tuple[str | None, str | None]:
        calls.append((source, law_id))
        return ("2022-01-01", "t")

    probes = probe_open_law(corpus, fetch=fake)
    assert calls == [("eu", "32016R0679")]
    assert len(probes) == 2
    assert [p.grounding_index for p in probes] == [0, 1]


def test_run_check_wires_open_law_fetch_without_url_probes(tmp_path: Path, monkeypatch) -> None:
    root = write_corpus(tmp_path, _open_law_doc())
    corpus = load_corpus(root)
    monkeypatch.setattr(check_mod, "probe_sources", lambda _corpus: [])
    report = run_check(
        corpus,
        today=date(2026, 10, 4),
        days=30,
        sources=True,
        open_law_fetch=lambda _s, _i: ("2025-01-01", "new text"),
    )
    assert report.probes == []
    assert len(report.open_law) == 1
    assert report.open_law[0].problem == "amended"


def test_run_check_without_sources_skips_open_law(tmp_path: Path) -> None:
    root = write_corpus(tmp_path, _open_law_doc())
    corpus = load_corpus(root)
    report = run_check(corpus, today=date(2026, 10, 4), days=30, sources=False)
    assert report.open_law == []