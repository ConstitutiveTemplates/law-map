"""Schema-v2 rules: source_kind/primary, review, negative_history, hashes, L2 gates, migrate."""

from __future__ import annotations

import copy
from hashlib import sha256
from pathlib import Path

import yaml

from law_map.checkspecs import validate_check_spec
from law_map.loader import load_corpus
from law_map.migrate import infer_source_kind, migrate_document, migrate_tree
from law_map.model import grounding_review_status, obligation_review_status
from law_map.openlaw import apply_hash_updates, collect_hash_updates, probe_open_law

from .test_model import VALID_OBLIGATION, write_corpus


def _doc(**overrides: object) -> dict:
    doc = yaml.safe_load(yaml.safe_dump(VALID_OBLIGATION))
    doc.update(overrides)
    return doc


def test_missing_source_kind_is_error(tmp_path: Path) -> None:
    doc = _doc()
    del doc["groundings"][0]["source_kind"]
    corpus = load_corpus(write_corpus(tmp_path, doc))
    assert any("source_kind must be one of" in e for e in corpus.errors)


def test_obligation_without_primary_is_error(tmp_path: Path) -> None:
    doc = _doc()
    doc["groundings"][0]["source_kind"] = "unofficial"
    corpus = load_corpus(write_corpus(tmp_path, doc))
    assert any("at least one grounding must have" in e and "primary" in e for e in corpus.errors)


def test_unofficial_host_claiming_primary_warns(tmp_path: Path) -> None:
    doc = _doc()
    doc["groundings"][0]["sources"] = ["https://law.justia.com/cases/x"]
    corpus = load_corpus(write_corpus(tmp_path, doc))
    assert corpus.ok(), corpus.errors
    assert any("mark it 'unofficial'" in w for w in corpus.warnings)


def test_unknown_jurisdiction_rejected(tmp_path: Path) -> None:
    doc = _doc()
    doc["groundings"][0]["jurisdiction"] = "XX"
    corpus = load_corpus(write_corpus(tmp_path, doc))
    assert any("must be an ISO 3166-1 alpha-2 code" in e for e in corpus.errors)


def test_eu_exception_accepted(tmp_path: Path) -> None:
    doc = _doc()
    doc["groundings"][0]["jurisdiction"] = "EU"
    assert load_corpus(write_corpus(tmp_path, doc)).ok()


def test_review_shape_and_draft(tmp_path: Path) -> None:
    doc = _doc()
    assert obligation_review_status(load_corpus(write_corpus(tmp_path, doc)).obligations[0]) == "draft"
    doc["reviewed_by"] = {"handle": "@expert", "domain": "JP data protection"}
    doc["reviewed_on"] = "2026-10-01"
    corpus = load_corpus(write_corpus(tmp_path, doc))
    assert corpus.ok(), corpus.errors
    assert obligation_review_status(corpus.obligations[0]) == "reviewed"
    assert grounding_review_status(corpus.obligations[0].data["groundings"][0]) == "draft"


def test_bad_review_shape_errors(tmp_path: Path) -> None:
    doc = _doc()
    doc["reviewed_by"] = {"handle": "@expert"}
    corpus = load_corpus(write_corpus(tmp_path, doc))
    assert any("reviewed_by.domain must be a non-empty string" in e for e in corpus.errors)


def test_negative_history_requires_holding(tmp_path: Path) -> None:
    doc = _doc()
    doc["groundings"][0]["negative_history"] = [{"date": "2018-06-06"}]
    corpus = load_corpus(write_corpus(tmp_path, doc))
    assert any("must state a non-empty 'holding'" in e for e in corpus.errors)
    doc["groundings"][0]["negative_history"] = [{"date": "2018-06-06", "holding": "vacated"}]
    assert load_corpus(write_corpus(tmp_path, doc)).ok()


def test_verified_hash_shape(tmp_path: Path) -> None:
    doc = _doc()
    doc["groundings"][0]["verified_text_sha256"] = "not-a-hash"
    corpus = load_corpus(write_corpus(tmp_path, doc))
    assert any("verified_text_sha256 must be a 64-character" in e for e in corpus.errors)


def test_strength_enum(tmp_path: Path) -> None:
    doc = _doc()
    doc["groundings"][0]["strength"] = "ironclad"
    corpus = load_corpus(write_corpus(tmp_path, doc))
    assert any("strength must be one of" in e for e in corpus.errors)


def test_confidence_enum(tmp_path: Path) -> None:
    doc = _doc()
    doc["groundings"][0]["confidence"] = "certain"
    corpus = load_corpus(write_corpus(tmp_path, doc))
    assert any("confidence must be one of" in e for e in corpus.errors)
    for level in ("high", "medium", "low"):
        doc["groundings"][0]["confidence"] = level
        assert load_corpus(write_corpus(tmp_path, doc)).ok(), level


def test_changed_hash_detected(tmp_path: Path) -> None:
    doc = _doc()
    doc["groundings"][0]["open_law"] = {"source": "eu", "id": "32016R0679"}
    doc["groundings"][0]["verified_text_sha256"] = sha256(b"old text").hexdigest()
    corpus = load_corpus(write_corpus(tmp_path, doc))
    assert corpus.ok(), corpus.errors
    probes = probe_open_law(corpus, fetch=lambda _s, _i: ("2022-01-01", "new text"))
    assert probes[0].problem == "changed"


def test_matching_hash_is_clean(tmp_path: Path) -> None:
    doc = _doc()
    doc["groundings"][0]["open_law"] = {"source": "eu", "id": "32016R0679"}
    doc["groundings"][0]["verified_text_sha256"] = sha256(b"same text").hexdigest()
    corpus = load_corpus(write_corpus(tmp_path, doc))
    probes = probe_open_law(corpus, fetch=lambda _s, _i: ("2022-01-01", "same text"))
    assert probes[0].problem is None


def test_record_hashes_round_trip(tmp_path: Path) -> None:
    doc = _doc()
    doc["groundings"][0]["open_law"] = {"source": "eu", "id": "32016R0679"}
    root = write_corpus(tmp_path, doc)
    corpus = load_corpus(root)
    updates = collect_hash_updates(corpus, fetch=lambda _s, _i: ("2022-01-01", "recorded text"))
    assert len(updates) == 1
    counts = apply_hash_updates(updates)
    assert sum(counts.values()) == 1
    reloaded = load_corpus(root)
    assert reloaded.ok(), reloaded.errors
    grounding = reloaded.obligations[0].data["groundings"][0]
    assert grounding["verified_text_sha256"] == sha256(b"recorded text").hexdigest()


def test_l2_without_fixtures_or_blocking_errors(tmp_path: Path) -> None:
    errors: list[str] = []
    validate_check_spec(
        {"id": "privacy/x", "obligation": "obligation.privacy.x", "level": "L2"},
        path=tmp_path / "checks" / "privacy" / "x.yml",
        errors=errors,
        known_ids=set(),
        repo_root=tmp_path,
    )
    assert any("'blocking' rule" in e for e in errors)
    assert any("'fixtures' list" in e for e in errors)


def test_l2_with_missing_fixture_errors(tmp_path: Path) -> None:
    errors: list[str] = []
    validate_check_spec(
        {
            "id": "privacy/x",
            "obligation": "obligation.privacy.x",
            "level": "L2",
            "blocking": "job fails",
            "fixtures": ["tests/fixtures/absent.py"],
        },
        path=tmp_path / "checks" / "privacy" / "x.yml",
        errors=errors,
        known_ids=set(),
        repo_root=tmp_path,
    )
    assert any("does not exist" in e for e in errors)


def test_migrate_document_v1_to_v2() -> None:
    v1 = {
        "version": 1,
        "id": "obligation.privacy.x",
        "groundings": [{"jurisdiction": "EU", "sources": ["https://eur-lex.europa.eu/eli/reg/2016/679/oj"]}],
    }
    migrated, notes = migrate_document(copy.deepcopy(v1))
    assert migrated["version"] == 2
    assert migrated["groundings"][0]["source_kind"] == "primary"
    assert notes


def test_migrate_rejects_non_v1() -> None:
    import pytest

    with pytest.raises(ValueError, match="not a schema-v1"):
        migrate_document({"version": 2})


def test_migrate_tree_round_trips_repo_v1(tmp_path: Path) -> None:
    import subprocess

    repo = Path(__file__).resolve().parent.parent
    proc = subprocess.run(
        ["git", "-C", str(repo), "show", "e8e3a23:obligations/privacy/no-cleartext-pii-logging.yml"],
        capture_output=True,
        text=True,
        check=True,
    )
    v1_root = tmp_path / "v1"
    (v1_root / "privacy").mkdir(parents=True)
    (v1_root / "privacy" / "no-cleartext-pii-logging.yml").write_text(proc.stdout, encoding="utf-8")
    out = tmp_path / "v2"
    report = migrate_tree(v1_root, out)
    assert "privacy/no-cleartext-pii-logging.yml" in report
    migrated = yaml.safe_load((out / "privacy" / "no-cleartext-pii-logging.yml").read_text(encoding="utf-8"))
    assert migrated["version"] == 2
    assert all("source_kind" in g for g in migrated["groundings"])


def test_infer_source_kind_hosts() -> None:
    assert infer_source_kind(["https://laws.e-gov.go.jp/law/x"]) == "primary"
    assert infer_source_kind(["https://web.archive.org/web/2020/https://x"]) == "unofficial"
    assert infer_source_kind(["https://dsgvo-gesetz.de/tdddg/"]) == "unofficial"
    assert infer_source_kind(["https://www.nist.gov/x"]) == "official-secondary"


def test_record_hashes_multi_grounding_with_urls(tmp_path: Path) -> None:
    """Span detection skips `- https://…` source items between groundings."""
    doc = yaml.safe_load(yaml.safe_dump(VALID_OBLIGATION))
    doc["groundings"][0]["open_law"] = {"source": "eu", "id": "32016R0679"}
    second = copy.deepcopy(doc["groundings"][0])
    second["open_law"] = {"source": "jp", "id": "other"}
    doc["groundings"].append(second)
    root = write_corpus(tmp_path, doc)
    corpus = load_corpus(root)
    updates = collect_hash_updates(corpus, fetch=lambda s, i: ("2022-01-01", f"text-{s}-{i}"))
    assert len(updates) == 2
    apply_hash_updates(updates)
    reloaded = load_corpus(root)
    assert reloaded.ok(), reloaded.errors
    hashes = [g["verified_text_sha256"] for g in reloaded.obligations[0].data["groundings"]]
    assert hashes[0] == sha256(b"text-eu-32016R0679").hexdigest()
    assert hashes[1] == sha256(b"text-jp-other").hexdigest()
