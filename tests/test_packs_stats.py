"""Corpus packs and the README stats block."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from law_map import cli
from law_map import stats as stats_mod
from law_map.loader import load_corpus
from law_map.model import PACKS, SOURCE_TYPE_PACK, SOURCE_TYPES, Obligation, obligation_pack
from law_map.refs import check_cross_references

from .test_model import VALID_OBLIGATION, write_corpus

REPO = Path(__file__).resolve().parent.parent


def _doc(slug: str, *source_types: str, **extra: object) -> dict:
    doc = copy.deepcopy(VALID_OBLIGATION)
    doc["id"] = f"obligation.privacy.{slug}"
    doc["enforcement"] = {"level": "L0", "check_refs": []}
    base = doc["groundings"][0]
    doc["groundings"] = [{**base, "source_type": t} for t in source_types]
    doc.update(extra)
    return doc


def test_every_source_type_has_a_pack() -> None:
    assert set(SOURCE_TYPE_PACK) == SOURCE_TYPES
    assert set(SOURCE_TYPE_PACK.values()) == set(PACKS)


@pytest.mark.parametrize(
    ("source_types", "pack"),
    [
        (("standard", "precedent"), "core"),
        (("guidance", "private_rule"), "guidance"),
        (("incident_report",), "community"),
        (("private_rule", "incident_report"), "community"),
    ],
)
def test_obligation_pack_is_strongest_grounding(source_types: tuple[str, ...], pack: str) -> None:
    ob = Obligation(path=Path("x.yml"), data=_doc("x", *source_types))
    assert obligation_pack(ob) == pack


def test_pack_selection_keeps_cross_pack_links(tmp_path: Path) -> None:
    lesson = _doc("lesson", "incident_report")
    law = _doc("law", "statute", requires=[lesson["id"]])
    root = write_corpus(tmp_path, law, lesson)
    corpus = load_corpus(root, packs=["core"])
    check_cross_references(corpus)
    assert [ob.id for ob in corpus.obligations] == [law["id"]]
    assert [ob.id for ob in corpus.excluded] == [lesson["id"]]
    assert corpus.ok(), corpus.errors


def test_excluded_pack_still_validated(tmp_path: Path) -> None:
    bad = _doc("bad", "incident_report", severity="apocalyptic")
    root = write_corpus(tmp_path, _doc("law", "statute"), bad)
    corpus = load_corpus(root, packs=["core"])
    assert any("severity" in e for e in corpus.errors)


def test_cli_pack_option(tmp_path: Path, capsys) -> None:
    root = write_corpus(tmp_path, _doc("law", "statute"), _doc("lesson", "incident_report"))
    assert cli.main(["--root", str(root), "--pack", "community", "list"]) == 0
    assert capsys.readouterr().out.split() == ["obligation.privacy.lesson"]


def test_reviewed_on_must_be_iso(tmp_path: Path) -> None:
    doc = _doc("law", "statute")
    doc["groundings"][0]["reviewed_on"] = "last week"
    corpus = load_corpus(write_corpus(tmp_path, doc))
    assert any("reviewed_on must be an ISO date" in e for e in corpus.errors)


def test_markdown_counts_binding_levels_and_gaps(tmp_path: Path) -> None:
    law = _doc("law", "statute", "guidance")
    law["groundings"][0]["reviewed_on"] = "2026-10-01"
    lesson = _doc("lesson", "incident_report")
    lesson["groundings"][0]["jurisdiction"] = "KR"
    corpus = load_corpus(write_corpus(tmp_path, law, lesson))
    out = stats_mod.render_markdown(corpus)
    assert "**2 obligations, 3 groundings, 2 jurisdictions.**" in out
    assert "| Japan (JP) | 2 | 1 | 0 | 1 | 0 | 2026-10-01 | 2027-03-31 |" in out
    assert "| South Korea (KR) | 1 | 0 | 0 | 0 | 1 | — | 2027-03-31 |" in out
    assert "| Japan (JP) | — | — | — | — | — | 1 | — | — |" in out
    assert "| `community` | 1 | 1 |" in out


def test_check_and_write_block(tmp_path: Path, capsys) -> None:
    root = write_corpus(tmp_path, _doc("law", "statute"))
    readme = tmp_path / "README.md"
    readme.write_text(f"# x\n\n{stats_mod.BEGIN_MARKER}\nstale\n{stats_mod.END_MARKER}\n\ntail\n", encoding="utf-8")
    args = ["--root", str(root), "stats", "--markdown"]
    assert cli.main([*args, "--check", str(readme)]) == 1
    assert "stale" in capsys.readouterr().err
    assert cli.main([*args, "--write", str(readme)]) == 0
    assert cli.main([*args, "--check", str(readme)]) == 0
    assert readme.read_text(encoding="utf-8").endswith(f"{stats_mod.END_MARKER}\n\ntail\n")


def test_check_without_markers_fails(tmp_path: Path, capsys) -> None:
    root = write_corpus(tmp_path, _doc("law", "statute"))
    readme = tmp_path / "README.md"
    readme.write_text("# no markers\n", encoding="utf-8")
    assert cli.main(["--root", str(root), "stats", "--markdown", "--check", str(readme)]) == 1
    assert "missing stats markers" in capsys.readouterr().err


def test_repo_readme_stats_in_sync() -> None:
    """The README scope tables are generated: run `just stats` after corpus edits."""
    corpus = load_corpus(REPO / "obligations")
    assert stats_mod.check_block(REPO / "README.md", stats_mod.render_markdown(corpus))


def test_empty_pack_selection_fails(tmp_path: Path, capsys) -> None:
    root = write_corpus(tmp_path, _doc("law", "statute"))
    assert cli.main(["--root", str(root), "--pack", "community", "validate"]) == 1
    assert "no obligations in pack(s) community" in capsys.readouterr().err
