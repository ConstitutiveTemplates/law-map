"""Corpus loading and validation rules."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from law_map.model import (
    check_codex_coverage,
    check_codex_sections,
    check_cross_references,
    codex_section_path,
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
        (
            lambda d: d["groundings"][0].__setitem__("open_law", "jp"),
            "open_law must be a mapping",
        ),
        (
            lambda d: d["groundings"][0].__setitem__("open_law", {"source": "jp"}),
            "open_law.id must be a non-empty string",
        ),
        (
            lambda d: d["groundings"][0].__setitem__("open_law", {"source": "", "id": "x"}),
            "open_law.source must be a non-empty string",
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


def test_cross_reference_singleton_related_section_is_quiet(tmp_path: Path) -> None:
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
    assert not any("unknown-section" in w for w in corpus.warnings)
    assert not any("shared-section" in w for w in corpus.warnings)


def _write_codex(tmp_path: Path) -> Path:
    """A minimal good-future-codex checkout: real section files laid out per
    the ``<tier>-<slug>`` naming rule (sections/<tier>/<slug>.md.jinja)."""
    codex = tmp_path / "codex"
    sections = codex / "sections"
    (sections / "baseline").mkdir(parents=True)
    (sections / "baseline" / "personal-data.md.jinja").write_text(
        "{# ethics: id=baseline-personal-data #}\n", encoding="utf-8"
    )
    (sections / "evolving").mkdir()
    (sections / "evolving" / "new-section.md.jinja").write_text(
        "{# ethics: id=evolving-new-section #}\n", encoding="utf-8"
    )
    return codex


def test_codex_section_path_resolves_by_tier_and_slug(tmp_path: Path) -> None:
    codex = _write_codex(tmp_path)
    target = codex_section_path(codex, "baseline-personal-data")
    assert target == codex / "sections" / "baseline" / "personal-data.md.jinja"
    assert target.is_file()
    assert codex_section_path(codex, "evolving-new-section").is_file()


def test_codex_section_path_rejects_malformed_ids(tmp_path: Path) -> None:
    codex = tmp_path / "codex"
    assert codex_section_path(codex, "personal-data") is None  # no tier prefix
    assert codex_section_path(codex, "baseline-") is None  # empty slug
    assert codex_section_path(codex, "") is None


def test_codex_missing_checkout_errors_on_every_section(tmp_path: Path) -> None:
    doc_a = yaml.safe_load(yaml.safe_dump(VALID_OBLIGATION))
    doc_a["enforcement"]["check_refs"] = []
    root = write_corpus(tmp_path, doc_a)
    corpus = load_corpus(root)
    errors = check_codex_sections(corpus, tmp_path / "nonexistent")
    assert len(errors) == 1
    assert "does not resolve" in errors[0]


def test_codex_unknown_related_section_errors(tmp_path: Path) -> None:
    codex = _write_codex(tmp_path)
    doc_a = yaml.safe_load(yaml.safe_dump(VALID_OBLIGATION))
    doc_a["related_sections"] = ["baseline-personal-data", "not-a-real-section"]
    doc_a["enforcement"]["check_refs"] = []
    root = write_corpus(tmp_path, doc_a)
    corpus = load_corpus(root)
    check_cross_references(corpus, checks_root=None, codex_root=codex)
    assert not corpus.ok()
    assert any("related_sections 'not-a-real-section' does not resolve" in e for e in corpus.errors)
    # known ids must not error, and the weak sharing warning is suppressed
    assert not any("referenced by no other obligation" in w for w in corpus.warnings)


def test_codex_known_section_passes_without_warning(tmp_path: Path) -> None:
    codex = _write_codex(tmp_path)
    doc_a = yaml.safe_load(yaml.safe_dump(VALID_OBLIGATION))
    doc_a["related_sections"] = ["evolving-new-section"]
    doc_a["enforcement"]["check_refs"] = []
    root = write_corpus(tmp_path, doc_a)
    corpus = load_corpus(root)
    check_cross_references(corpus, checks_root=None, codex_root=codex)
    assert corpus.ok(), corpus.errors
    assert not any("referenced by no other obligation" in w for w in corpus.warnings)


def test_open_law_ref_valid_shape_passes(tmp_path: Path) -> None:
    doc = yaml.safe_load(yaml.safe_dump(VALID_OBLIGATION))
    doc["groundings"][0]["open_law"] = {"source": "jp", "id": "415AC0000000057"}
    root = write_corpus(tmp_path, doc)
    corpus = load_corpus(root)
    assert corpus.ok(), corpus.errors


def test_codex_coverage_warns_for_unreferenced_sections(tmp_path: Path) -> None:
    codex = _write_codex(tmp_path)  # baseline-personal-data, evolving-new-section
    doc_a = yaml.safe_load(yaml.safe_dump(VALID_OBLIGATION))
    doc_a["related_sections"] = ["baseline-personal-data"]
    doc_a["enforcement"]["check_refs"] = []
    root = write_corpus(tmp_path, doc_a)
    corpus = load_corpus(root)
    warnings = check_codex_coverage(corpus, codex)
    assert len(warnings) == 1
    assert "evolving-new-section" in warnings[0]
    assert "no referencing obligation" in warnings[0]


def test_codex_coverage_clean_when_all_referenced(tmp_path: Path) -> None:
    codex = _write_codex(tmp_path)
    doc_a = yaml.safe_load(yaml.safe_dump(VALID_OBLIGATION))
    doc_a["related_sections"] = ["baseline-personal-data", "evolving-new-section"]
    doc_a["enforcement"]["check_refs"] = []
    root = write_corpus(tmp_path, doc_a)
    corpus = load_corpus(root)
    assert check_codex_coverage(corpus, codex) == []


def test_codex_coverage_missing_checkout_is_empty(tmp_path: Path) -> None:
    root = write_corpus(tmp_path, VALID_OBLIGATION)
    corpus = load_corpus(root)
    assert check_codex_coverage(corpus, tmp_path / "nonexistent") == []


def test_cross_references_with_codex_adds_reverse_warnings_not_errors(tmp_path: Path) -> None:
    codex = _write_codex(tmp_path)
    doc_a = yaml.safe_load(yaml.safe_dump(VALID_OBLIGATION))
    doc_a["related_sections"] = ["baseline-personal-data"]
    doc_a["enforcement"]["check_refs"] = []
    root = write_corpus(tmp_path, doc_a)
    corpus = load_corpus(root)
    check_cross_references(corpus, checks_root=None, codex_root=codex)
    assert corpus.ok(), corpus.errors
    assert any(
        "evolving-new-section" in w and "no referencing obligation" in w for w in corpus.warnings
    )


def test_scheduled_but_already_effective_warns(tmp_path: Path) -> None:
    from datetime import date

    doc = yaml.safe_load(yaml.safe_dump(VALID_OBLIGATION))
    doc["groundings"][0]["status"] = "scheduled"
    doc["groundings"][0]["effective"] = "2026-08-02"
    root = write_corpus(tmp_path, doc)
    corpus = load_corpus(root, today=date(2026, 10, 4))
    assert corpus.ok(), corpus.errors
    assert any(
        "scheduled" in w and "already past" in w for w in corpus.warnings
    ), corpus.warnings


def test_scheduled_with_future_effective_is_quiet(tmp_path: Path) -> None:
    from datetime import date

    doc = yaml.safe_load(yaml.safe_dump(VALID_OBLIGATION))
    doc["groundings"][0]["status"] = "scheduled"
    doc["groundings"][0]["effective"] = "2027-12-11"
    root = write_corpus(tmp_path, doc)
    corpus = load_corpus(root, today=date(2026, 10, 4))
    assert corpus.ok(), corpus.errors
    assert not any("already past" in w for w in corpus.warnings), corpus.warnings


def test_obligation_without_check_refs_warns(tmp_path: Path) -> None:
    """Predicate is check_refs emptiness only — no enforcement block warns too."""
    from datetime import date

    doc = yaml.safe_load(yaml.safe_dump(VALID_OBLIGATION))
    doc.pop("enforcement", None)
    root = write_corpus(tmp_path, doc)
    corpus = load_corpus(root, today=date(2026, 10, 4))
    assert corpus.ok(), corpus.errors
    assert any("check_refs" in w for w in corpus.warnings), corpus.warnings


def test_obligation_with_check_refs_is_quiet(tmp_path: Path) -> None:
    from datetime import date

    root = write_corpus(tmp_path, VALID_OBLIGATION)
    corpus = load_corpus(root, today=date(2026, 10, 4))
    assert corpus.ok(), corpus.errors
    assert not any("check_refs" in w for w in corpus.warnings), corpus.warnings