"""CLI smoke tests (offline)."""

from __future__ import annotations

from datetime import date

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