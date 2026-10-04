"""Corpus loading and validation rules."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from law_map.model import (
    check_cross_references,
    load_corpus,
)

VALID_OBLIGATION: dict = {
    "version": 1,
    "id": "obligation.privacy.valid-fixture",
    "title": "Valid fixture obligation",
    "category": "privacy",
    "modality": "prohibition",
    "severity": "critical",
    "summary": "A fully valid obligation used as the base fixture.",
    "scope": {
        "components": ["logging"],
        "data_types": ["email"],
        "excludes": "test canaries",
    },
    "groundings": [
        {
            "jurisdiction": "JP",
            "source_type": "statute",
            "status": "in_force",
            "authority": "APPI",
            "citation": "第23条",
            "effective": "2022-04-01",
            "review_by": "2027-03-31",
            "sources": ["https://www.ppc.go.jp/personalinfo/legal/"],
        }
    ],
    "conflicts": [],
    "requires": [],
    "directives": {"human": "instruction", "agent": "imperative"},
    "related_sections": ["baseline-personal-data"],
    "enforcement": {"level": "L1", "check_refs": ["privacy/valid-fixture"]},
}


def write_corpus(tmp_path: Path, *docs: dict) -> Path:
    root = tmp_path / "obligations"
    for i, doc in enumerate(docs):
        parts = str(doc["id"]).split(".")
        domain = parts[1] if len(parts) > 1 else "misc"
        domain_dir = root / domain
        domain_dir.mkdir(parents=True, exist_ok=True)
        (domain_dir / f"ob{i}.yml").write_text(yaml.safe_dump(doc), encoding="utf-8")
    return root


def test_valid_corpus_loads(tmp_path: Path) -> None:
    root = write_corpus(tmp_path, VALID_OBLIGATION)
    corpus = load_corpus(root)
    assert corpus.ok(), corpus.errors
    assert len(corpus.obligations) == 1
    assert corpus.obligations[0].id == "obligation.privacy.valid-fixture"


def test_example_file_excluded(tmp_path: Path) -> None:
    root = tmp_path / "obligations"
    root.mkdir()
    (root / "_example.yml").write_text(yaml.safe_dump(VALID_OBLIGATION), encoding="utf-8")
    (root / "privacy").mkdir()
    (root / "privacy" / "real.yml").write_text(yaml.safe_dump(VALID_OBLIGATION), encoding="utf-8")
    corpus = load_corpus(root)
    assert corpus.ok()
    assert len(corpus.obligations) == 1


def test_empty_or_missing_corpus() -> None:
    corpus = load_corpus(Path("/nonexistent/dir"))
    assert corpus.ok()
    assert corpus.obligations == []


@pytest.mark.parametrize(
    ("mutate", "needle"),
    [
        (lambda d: d.__setitem__("version", 2), "version must be 1"),
        (lambda d: d.__setitem__("id", "not-an-id"), "does not match pattern"),
        (lambda d: d.pop("title"), "missing required field 'title'"),
        (lambda d: d.pop("summary"), "missing required field 'summary'"),
        (lambda d: d.__setitem__("category", "nope"), "category must be one of"),
        (lambda d: d.__setitem__("modality", "must"), "modality must be one of"),
        (lambda d: d.__setitem__("severity", "fatal"), "severity must be one of"),
        (lambda d: d.__setitem__("groundings", []), "groundings must be a non-empty list"),
        (lambda d: d["groundings"].__setitem__(0, {"jurisdiction": "JP"}), "missing required field 'authority'"),
        (
            lambda d: d["groundings"][0].__setitem__("review_by", "2027/03/31"),
            "review_by must be an ISO date",
        ),
        (
            lambda d: d["groundings"][0].__setitem__("sources", ["ftp://example.com/x"]),
            "must contain only http/https URLs",
        ),
        (
            lambda d: d["groundings"][0].__setitem__("sources", []),
            "sources must be a non-empty list",
        ),
        (
            lambda d: d["groundings"][0].__setitem__("source_type", "executive_order"),
            "source_type must be one of",
        ),
        (lambda d: d["groundings"][0].__setitem__("status", "enacted"), "status must be one of"),
        (lambda d: d.__setitem__("scope", "not a mapping"), "scope must be a mapping"),
        (lambda d: d.__setitem__("conflicts", "x"), "conflicts must be a list"),
        (lambda d: d.__setitem__("requires", [42]), "requires must contain only obligation ids"),
        (lambda d: d.__setitem__("directives", {"human": "x"}), "missing required key 'agent'"),
        (
            lambda d: d["enforcement"].__setitem__("level", "L9"),
            "enforcement.level must be one of",
        ),
        (
            lambda d: d["groundings"][0].__setitem__("effective", "not-a-date"),
            "effective must be an ISO date",
        ),
    ],
)
def test_validation_rules_fire(tmp_path: Path, mutate, needle: str) -> None:
    doc = yaml.safe_load(yaml.safe_dump(VALID_OBLIGATION))
    mutate(doc)
    root = write_corpus(tmp_path, doc)
    corpus = load_corpus(root)
    assert not corpus.ok()
    assert any(needle in err for err in corpus.errors), corpus.errors


def test_duplicate_id_rejected(tmp_path: Path) -> None:
    root = write_corpus(tmp_path, VALID_OBLIGATION, VALID_OBLIGATION)
    corpus = load_corpus(root)
    assert any("duplicate id" in err for err in corpus.errors)


def test_id_domain_must_match_directory(tmp_path: Path) -> None:
    doc = yaml.safe_load(yaml.safe_dump(VALID_OBLIGATION))
    doc["id"] = "obligation.security.wrong-place"
    root = write_corpus(tmp_path, doc)  # placed under security/ (derived from id)
    target_dir = root / "privacy"
    target_dir.mkdir(exist_ok=True)
    (root / "security" / "ob0.yml").rename(target_dir / "ob0.yml")
    corpus = load_corpus(root)
    assert not corpus.ok()
    assert any("does not match directory" in err for err in corpus.errors)


def test_subdivision_with_wrong_jurisdiction_warns(tmp_path: Path) -> None:
    doc = yaml.safe_load(yaml.safe_dump(VALID_OBLIGATION))
    doc["groundings"][0]["subdivision"] = "ZZ"
    root = write_corpus(tmp_path, doc)
    corpus = load_corpus(root)
    assert corpus.ok()
    assert any("subdivision only allowed" in w for w in corpus.warnings)


def test_bad_yaml_is_error_not_exception(tmp_path: Path) -> None:
    root = tmp_path / "obligations"
    root.mkdir()
    (root / "broken.yml").write_text("version: [unclosed", encoding="utf-8")
    corpus = load_corpus(root)
    assert not corpus.ok()
    assert any("invalid YAML" in err for err in corpus.errors)


def test_cross_reference_missing_requires_and_check_ref(tmp_path: Path) -> None:
    doc = yaml.safe_load(yaml.safe_dump(VALID_OBLIGATION))
    doc["requires"] = ["obligation.security.missing"]
    root = write_corpus(tmp_path, doc)
    corpus = load_corpus(root)
    check_cross_references(corpus, checks_root=tmp_path / "checks")
    assert corpus.ok() is False
    assert any("requires 'obligation.security.missing' does not exist" in e for e in corpus.errors)
    assert any("check_refs 'privacy/valid-fixture' does not match" in e for e in corpus.errors)


def test_cross_reference_unknown_related_section_warns_only(tmp_path: Path) -> None:
    doc_a = yaml.safe_load(yaml.safe_dump(VALID_OBLIGATION))
    doc_a["related_sections"] = ["unknown-section", "shared-section"]
    doc_a["enforcement"]["check_refs"] = []
    doc_b = yaml.safe_load(yaml.safe_dump(VALID_OBLIGATION))
    doc_b["id"] = "obligation.security.valid-fixture-b"
    doc_b["category"] = "security"
    doc_b["related_sections"] = ["shared-section"]
    doc_b["enforcement"]["check_refs"] = []
    root = write_corpus(tmp_path, doc_a, doc_b)
    corpus = load_corpus(root)
    check_cross_references(corpus, checks_root=tmp_path / "checks")
    assert corpus.ok()
    assert any("unknown-section" in w for w in corpus.warnings)
    assert not any("shared-section" in w for w in corpus.warnings)