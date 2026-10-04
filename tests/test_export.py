"""Export renders codex-style sections with the required markers."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from law_map.export import export_obligations, render_obligation
from law_map.model import Obligation

from .test_model import VALID_OBLIGATION

FIXED_TODAY = date(2026, 10, 4)


def one_obligation() -> Obligation:
    return Obligation(path=Path("/unused/ob0.yml"), data=yaml.safe_load(yaml.safe_dump(VALID_OBLIGATION)))


def test_render_contains_required_markers() -> None:
    text = render_obligation(one_obligation(), today=FIXED_TODAY)
    assert "{# ethics: id=valid-fixture version=2026-10-04.1 status=draft" in text
    assert "triggers=[logging, privacy, prohibition]" in text
    assert "# Valid fixture obligation" in text
    assert "> 要約:" in text
    assert "## 事実" in text
    assert "### 1. JP — statute (in_force)" in text
    assert "APPI" in text
    assert "第23条" in text
    assert "https://www.ppc.go.jp/personalinfo/legal/" in text
    for heading in ("## 禁止パターン", "## 推奨設定", "## 運用チェック", "## 制度変更ウォッチ"):
        assert heading in text
    assert "確認TODO: JP grounding #1: review_by 2027-03-31" in text
    assert "本セクションは法的助言を構成しません" in text


def test_export_writes_one_file_per_obligation(tmp_path: Path) -> None:
    written = export_obligations([one_obligation()], tmp_path)
    assert len(written) == 1
    target = tmp_path / "valid-fixture.md.jinja"
    assert written[0] == target
    assert "{# ethics:" in target.read_text(encoding="utf-8")


def test_export_groundings_sorted_and_deterministic(tmp_path: Path) -> None:
    ob = one_obligation()
    first = export_obligations([ob], tmp_path / "a")[0].read_text(encoding="utf-8")
    second = export_obligations([ob], tmp_path / "b")[0].read_text(encoding="utf-8")
    assert first == second


def test_export_threads_today_through(tmp_path: Path) -> None:
    ob = one_obligation()
    text = export_obligations([ob], tmp_path, today=FIXED_TODAY)[0].read_text(encoding="utf-8")
    assert f"version={FIXED_TODAY.isoformat()}.1" in text