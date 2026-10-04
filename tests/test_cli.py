"""CLI smoke tests (offline)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import yaml

from law_map import check as check_mod
from law_map import cli

from .test_model import VALID_OBLIGATION


@pytest.fixture
def corpus_dir(tmp_path) -> str:
    root = tmp_path / "obligations"
    root.mkdir()
    (root / "privacy").mkdir()
    doc = yaml.safe_load(yaml.safe_dump(VALID_OBLIGATION))
    (root / "privacy" / "valid.yml").write_text(yaml.safe_dump(doc), encoding="utf-8")
    return str(root)


def test_validate_ok(corpus_dir: str, capsys) -> None:
    assert cli.main(["--root", corpus_dir, "validate"]) == 0
    assert "ok: 1 obligation(s)" in capsys.readouterr().out


def test_validate_errors_on_bad_corpus(tmp_path, capsys) -> None:
    root = tmp_path / "obligations"
    root.mkdir()
    (root / "bad.yml").write_text("version: 9\nid: nope\n", encoding="utf-8")
    assert cli.main(["--root", str(root), "validate"]) == 1
    assert "error:" in capsys.readouterr().err


def test_validate_empty_corpus(tmp_path, capsys) -> None:
    root = tmp_path / "obligations"
    root.mkdir()
    assert cli.main(["--root", str(root), "validate"]) == 0
    assert "ok: 0 obligation(s)" in capsys.readouterr().out


def test_validate_codex_unknown_section_errors(corpus_dir: str, tmp_path, capsys) -> None:
    codex = tmp_path / "codex"
    (codex / "sections" / "baseline").mkdir(parents=True)
    (codex / "sections" / "MANIFEST.yml").write_text(
        "sections:\n  - id: baseline-personal-data\n    file: baseline/personal-data.md.jinja\n",
        encoding="utf-8",
    )
    (codex / "sections" / "baseline" / "personal-data.md.jinja").write_text(
        "{# ethics: id=baseline-personal-data version=2026-09-01.1 status=active #}\n",
        encoding="utf-8",
    )
    for yml in Path(corpus_dir).rglob("*.yml"):
        doc = yaml.safe_load(yml.read_text(encoding="utf-8"))
        doc["related_sections"].append("not-a-real-section")
        yml.write_text(yaml.safe_dump(doc), encoding="utf-8")
    assert cli.main(["--root", corpus_dir, "validate", "--codex", str(codex), "--warnings"]) == 1
    assert "does not resolve" in capsys.readouterr().err


def test_validate_codex_known_section_ok(corpus_dir: str, tmp_path, capsys) -> None:
    codex = tmp_path / "codex"
    (codex / "sections" / "baseline").mkdir(parents=True)
    (codex / "sections" / "MANIFEST.yml").write_text(
        "sections:\n  - id: baseline-personal-data\n    file: baseline/personal-data.md.jinja\n",
        encoding="utf-8",
    )
    (codex / "sections" / "baseline" / "personal-data.md.jinja").write_text(
        "{# ethics: id=baseline-personal-data version=2026-09-01.1 status=active #}\n",
        encoding="utf-8",
    )
    assert cli.main(["--root", corpus_dir, "validate", "--codex", str(codex)]) == 0
    assert "ok: 1 obligation(s)" in capsys.readouterr().out


def test_list(corpus_dir: str, capsys) -> None:
    assert cli.main(["--root", corpus_dir, "list"]) == 0
    out = capsys.readouterr().out
    assert "obligation.privacy.valid-fixture" in out


def test_show(corpus_dir: str, capsys) -> None:
    assert cli.main(["--root", corpus_dir, "show", "valid-fixture"]) == 0
    out = capsys.readouterr().out
    assert "title: Valid fixture obligation" in out


def test_show_missing(corpus_dir: str, capsys) -> None:
    assert cli.main(["--root", corpus_dir, "show", "nope"]) == 1
    assert "no obligation matches" in capsys.readouterr().err


def test_check_expired_exits_1(tmp_path, monkeypatch, capsys) -> None:
    root = tmp_path / "obligations"
    root.mkdir()
    doc = yaml.safe_load(yaml.safe_dump(VALID_OBLIGATION))
    doc["groundings"][0]["review_by"] = "2020-01-01"
    (root / "ob0.yml").write_text(yaml.safe_dump(doc), encoding="utf-8")

    monkeypatch.setattr(check_mod, "today", lambda: date(2026, 10, 4))
    assert cli.main(["--root", str(root), "check"]) == 1
    assert "EXPIRED" in capsys.readouterr().out


def test_check_clean_exits_0(tmp_path, monkeypatch, capsys) -> None:
    root = tmp_path / "obligations"
    root.mkdir()
    doc = yaml.safe_load(yaml.safe_dump(VALID_OBLIGATION))
    doc["groundings"][0]["review_by"] = "2030-01-01"
    (root / "ob0.yml").write_text(yaml.safe_dump(doc), encoding="utf-8")

    monkeypatch.setattr(check_mod, "today", lambda: date(2026, 10, 4))
    assert cli.main(["--root", str(root), "check"]) == 0
    assert "0 expired" in capsys.readouterr().out


def test_export_smoke(corpus_dir: str, tmp_path, capsys) -> None:
    out = tmp_path / "out"
    assert cli.main(["--root", corpus_dir, "export", "--out", str(out)]) == 0
    assert (out / "valid-fixture.md.jinja").is_file()
    out_text = capsys.readouterr().out
    assert "wrote" in out_text


def test_export_empty_exits_1(tmp_path, capsys) -> None:
    root = tmp_path / "obligations"
    root.mkdir()
    assert cli.main(["--root", str(root), "export", "--out", str(tmp_path / "o")]) == 1


def _write_codex(tmp_path) -> Path:
    """Minimal codex checkout: sections/baseline/personal-data.md.jinja exists."""
    codex = tmp_path / "codex"
    (codex / "sections" / "baseline").mkdir(parents=True)
    (codex / "sections" / "baseline" / "personal-data.md.jinja").write_text(
        "{# ethics: id=baseline-personal-data #}\n", encoding="utf-8"
    )
    return codex


def test_check_codex_clean_exits_0(corpus_dir: str, tmp_path, capsys) -> None:
    codex = _write_codex(tmp_path)
    assert cli.main(["--root", corpus_dir, "check", "--codex", str(codex)]) == 0
    assert "0 expired" in capsys.readouterr().out


def test_check_codex_broken_checkout_exits_1(corpus_dir: str, tmp_path, capsys) -> None:
    codex = tmp_path / "codex"  # no sections/ directory at all
    assert cli.main(["--root", corpus_dir, "check", "--codex", str(codex)]) == 1
    assert "not a good-future-codex checkout" in capsys.readouterr().err


def test_check_codex_unresolved_section_exits_1(corpus_dir: str, tmp_path, capsys) -> None:
    codex = tmp_path / "codex"
    (codex / "sections").mkdir(parents=True)  # sections/ exists but personal-data.md.jinja is missing
    assert cli.main(["--root", corpus_dir, "check", "--codex", str(codex)]) == 1
    err = capsys.readouterr().err
    assert "related_sections 'baseline-personal-data' does not resolve" in err


def test_validate_codex_clean_exits_0(corpus_dir: str, tmp_path, capsys) -> None:
    codex = _write_codex(tmp_path)
    assert cli.main(["--root", corpus_dir, "validate", "--codex", str(codex)]) == 0
    assert "ok: 1 obligation(s)" in capsys.readouterr().out


def test_validate_codex_unresolved_section_exits_1(corpus_dir: str, tmp_path, capsys) -> None:
    codex = tmp_path / "codex"
    (codex / "sections").mkdir(parents=True)
    assert cli.main(["--root", corpus_dir, "validate", "--codex", str(codex)]) == 1
    assert "does not resolve" in capsys.readouterr().err