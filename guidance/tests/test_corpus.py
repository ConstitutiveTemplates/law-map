"""Offline tests for the front matter contract and the generated MANIFEST."""

from __future__ import annotations

import copy
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import validate as v
from validation.manifest import (
    VOCAB_BEGIN,
    build_manifest,
    expected_outputs,
    stale_outputs,
)
from validation.vocabulary import pack_for

REPO = Path(__file__).resolve().parent.parent
SAMPLE = REPO / "sections" / "baseline" / "pki-chain.md"


@pytest.fixture(autouse=True)
def _clean_sinks() -> Iterator[None]:
    v.reset()
    yield
    v.reset()


@pytest.fixture
def vocab() -> dict:
    return v.load_vocabulary()


@pytest.fixture
def front() -> dict:
    data, _ = v.read_section(SAMPLE)
    assert data is not None
    return data


def test_corpus_validates() -> None:
    v.validate_corpus()
    assert v.errors == []


def test_no_jinja_files_remain() -> None:
    assert list((REPO / "sections").rglob("*.jinja")) == []


def test_generated_outputs_in_sync() -> None:
    assert stale_outputs(expected_outputs()) == []


def test_manifest_lists_every_section_file() -> None:
    manifest = build_manifest()
    files = {row["file"] for row in manifest["sections"]}
    on_disk = {p.relative_to(REPO / "sections").as_posix() for p in v.section_files()}
    assert files == on_disk
    assert all(row["id"] == v.expected_id(REPO / "sections" / row["file"]) for row in manifest["sections"])


def test_sample_front_matter_is_clean(front: dict, vocab: dict) -> None:
    v.check_front_matter(SAMPLE, front, vocab)
    assert v.errors == []


@pytest.mark.parametrize(
    ("mutate", "needle"),
    [
        (lambda f: f.update(when=["cli", "nonsense"]), "not in VOCABULARY.yml"),
        (lambda f: f.update(extra=1), "unknown front matter key 'extra'"),
        (lambda f: f.pop("en"), "front matter missing 'en'"),
        (lambda f: f.update(license="Apache-2.0"), "license must be 'CC-BY-4.0'"),
        (lambda f: f.update(version="2026-09-21"), "version must be"),
        (lambda f: f.update(id="baseline-other"), "path-derived id"),
        (lambda f: f["triggers"].update(pattern="(unclosed"), "triggers.pattern does not compile"),
        (lambda f: f["en"].update(prohibited=[]), "en.prohibited must be a non-empty string list"),
        (lambda f: f.update(obligations=["privacy.no-logging"]), "is not 'obligation.<category>.<slug>'"),
    ],
)
def test_front_matter_errors(front: dict, vocab: dict, mutate, needle: str) -> None:
    bad = copy.deepcopy(front)
    mutate(bad)
    v.check_front_matter(SAMPLE, bad, vocab)
    assert any(needle in msg for msg in v.errors), v.errors


@pytest.mark.parametrize(
    "text",
    [
        "出典: 文化庁(REGISTRY.ymlに記録)。",
        "> 配布: library / cli / kaggle / mcp。",
        "> Triggers: `(?i)\\bntp\\b`.",
        "- 設定側トリガー(Copier QA L1用):",
        "see `_shared/ethics/lang/copyright-terms.yml`",
        "gate on scraping_effective",
        "renamed from good-future-codex",
    ],
)
def test_banned_phrases(text: str) -> None:
    v.check_banned_phrases(SAMPLE, text, "body")
    assert v.errors, text


def test_banned_phrases_allow_ordinary_prose() -> None:
    v.check_banned_phrases(SAMPLE, "> 規模: 世界問題。CLI ツールでも library でも同じ。再配布は別の権利。", "body")
    assert v.errors == []


@pytest.mark.parametrize(
    ("when", "pack"),
    [
        (["oj_code"], "competitive-programming"),
        (["oj_code", "kaggle"], "competitive-programming"),
        (["data_science", "kaggle"], "core"),
        (["embedded", "oj_code"], "core"),
        (["embedded"], "embedded"),
        (["always"], "core"),
    ],
)
def test_pack_for(vocab: dict, when: list[str], pack: str) -> None:
    assert pack_for(when, vocab) == pack


def test_review_by_optional_with_obligations() -> None:
    assert v.check_review_by(SAMPLE, "## 制度変更ウォッチ\n- none\n", required=False) == []
    assert v.errors == []
    v.check_review_by(SAMPLE, "## 制度変更ウォッチ\n- none\n")
    assert v.errors


def test_docs_carry_generated_vocabulary() -> None:
    for name in ("README.md", "CONTRIBUTING.md"):
        assert VOCAB_BEGIN in (REPO / name).read_text(encoding="utf-8"), name


def test_template_front_matter_has_every_key() -> None:
    data, body = v.read_section(REPO / "sections" / "_template.md")
    assert data is not None
    assert set(data) == set(v.FRONT_MATTER_KEYS)
    v.check_banned_phrases(REPO / "sections" / "_template.md", body, "template")
    assert v.errors == []


def test_license_note_required() -> None:
    v.check_license_note(SAMPLE, "# t\n\nbody\n", "baseline-pki-chain")
    assert v.errors
    v.reset()
    body = SAMPLE.read_text(encoding="utf-8")
    v.check_license_note(SAMPLE, body, "baseline-pki-chain")
    assert v.errors == []
    v.check_license_note(SAMPLE, body, "baseline-other")
    assert v.errors
