"""Export renders guidance-format section drafts with the required front matter."""

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


REPO_ROOT = Path(__file__).resolve().parent.parent


def section_parts(text: str) -> tuple[dict, str]:
    """Split the leading ``---`` YAML block from the markdown body."""
    assert text.startswith("---\n")
    _open, rest = text.split("---\n", 1)
    front_text, _, body = rest.partition("\n---\n")
    assert body, "missing closing front matter fence"
    return yaml.safe_load(front_text), body


def test_render_front_matter_mirrors_section_contract() -> None:
    text = render_obligation(one_obligation(), today=FIXED_TODAY)
    front, _body = section_parts(text)
    assert front["id"] == "draft-valid-fixture"
    assert front["version"] == "2026-10-04.1"
    assert front["status"] == "draft"
    assert front["placement"] == "agents_md"
    assert front["when"] == ["personal_data"]
    assert front["obligations"] == ["obligation.privacy.valid-fixture"]
    assert front["license"] == "CC-BY-4.0"
    assert front["triggers"]["keywords"] == ["logging", "privacy", "prohibition"]
    assert "logging" in front["triggers"]["pattern"]
    assert front["sources"] == ["https://www.ppc.go.jp/personalinfo/legal/"]
    assert front["en"]["title"] == "Valid fixture obligation"
    assert "A fully valid obligation used as the base fixture." in front["en"]["summary"]
    assert "imperative" in front["en"]["prohibited"][0]


def test_render_body_keeps_skeleton_headings() -> None:
    text = render_obligation(one_obligation(), today=FIXED_TODAY)
    _front, body = section_parts(text)
    assert body.startswith("# Valid fixture obligation\n")
    assert "> 要約:" in body
    assert "## 事実" in body
    assert "### 1. JP — statute (in_force)" in body
    assert "APPI" in body
    assert "第23条" in body
    assert "https://www.ppc.go.jp/personalinfo/legal/" in body
    for heading in ("## 禁止パターン", "## 推奨設定", "## 運用チェック", "## 制度変更ウォッチ"):
        assert heading in body
    assert "確認TODO: JP grounding #1: review_by 2027-03-31" in body
    assert "本セクションは法的助言を構成しません" in body
    assert "{# ethics:" not in text
    assert "{{" not in body and "{%" not in body
    last = body.rstrip("\n").splitlines()[-1]
    assert last == (
        "<!-- © kanon contributors (https://github.com/politeuma/kanon). "
        "Section draft-valid-fixture, licensed CC BY 4.0: https://creativecommons.org/licenses/by/4.0/ -->"
    )


def test_render_draft_passes_section_validators(tmp_path: Path) -> None:
    import sys

    text = render_obligation(one_obligation(), today=FIXED_TODAY)
    probe_dir = tmp_path / "sections" / "draft"
    probe_dir.mkdir(parents=True)
    probe = probe_dir / "valid-fixture.md"
    probe.write_text(text, encoding="utf-8")
    tools_dir = REPO_ROOT / "guidance" / "tools"
    sys.path.insert(0, str(tools_dir))
    try:
        from validation.corpus import check_front_matter  # type: ignore[import-not-found]
        from validation.frontmatter import read_section  # type: ignore[import-not-found]
        from validation.vocabulary import load_vocabulary  # type: ignore[import-not-found]

        vocab = load_vocabulary(REPO_ROOT / "guidance" / "sections" / "VOCABULARY.yml")
        front, _body = read_section(probe)
        assert isinstance(front, dict)
        from validation import report  # type: ignore[import-not-found]

        report.reset()
        check_front_matter(probe, front, vocab)
        assert report.errors == [], report.errors
    finally:
        sys.path.remove(str(tools_dir))


def test_export_writes_one_file_per_obligation(tmp_path: Path) -> None:
    written = export_obligations([one_obligation()], tmp_path)
    assert len(written) == 1
    target = tmp_path / "valid-fixture.md"
    assert written[0] == target
    assert target.read_text(encoding="utf-8").startswith("---\n")


def test_export_groundings_sorted_and_deterministic(tmp_path: Path) -> None:
    ob = one_obligation()
    first = export_obligations([ob], tmp_path / "a")[0].read_text(encoding="utf-8")
    second = export_obligations([ob], tmp_path / "b")[0].read_text(encoding="utf-8")
    assert first == second


def test_export_threads_today_through(tmp_path: Path) -> None:
    ob = one_obligation()
    text = export_obligations([ob], tmp_path, today=FIXED_TODAY)[0].read_text(encoding="utf-8")
    assert 'version: "2026-10-04.1"' in text


def test_export_uses_check_spec_triggers(tmp_path: Path) -> None:
    checks = tmp_path / "checks" / "privacy"
    checks.mkdir(parents=True)
    (checks / "valid-fixture.yml").write_text(
        yaml.safe_dump({"triggers": ["(?i)\\b(pii|privacy)\\b", "(?i)\\b(pii)\\b"]}), encoding="utf-8"
    )
    text = export_obligations([one_obligation()], tmp_path / "out", checks_root=tmp_path / "checks")[0].read_text(
        encoding="utf-8"
    )
    front, _body = section_parts(text)
    assert front["triggers"]["pattern"] == "(?i)\\b(pii|privacy)\\b"
    assert front["triggers"]["config"] == "(?i)\\b(pii)\\b"


def test_render_when_falls_back_to_always() -> None:
    ob = one_obligation()
    ob.data["category"] = "security"
    ob.data["scope"] = {"components": ["repository"]}
    assert render_obligation(ob, today=FIXED_TODAY).startswith("---\n")
    front, _body = section_parts(render_obligation(ob, today=FIXED_TODAY))
    assert front["when"] == ["always"]


def test_render_contains_directives_and_enforcement() -> None:
    text = render_obligation(one_obligation(), today=FIXED_TODAY)
    _front, body = section_parts(text)
    assert "## Directives" in body
    # Directives sit after the summary, before the grounding facts.
    assert body.index("## Directives") > body.index("> 要約:")
    assert body.index("## Directives") < body.index("## 事実")
    assert "- human: instruction" in body
    assert "- agent: imperative" in body
    assert "- enforcement: level=L1 check_refs=[checks/privacy/valid-fixture.yml]" in body


def test_render_without_directives_or_enforcement_omits_section() -> None:
    ob = one_obligation()
    ob.data.pop("directives", None)
    ob.data.pop("enforcement", None)
    text = render_obligation(ob, today=FIXED_TODAY)
    assert "## Directives" not in text
    front, _body = section_parts(text)
    assert front["en"]["prohibited"] == ["A fully valid obligation used as the base fixture."]
