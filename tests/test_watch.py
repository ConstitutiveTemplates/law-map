"""law-watch: amendment feeds for cited instruments (offline, injected fetch)."""

from __future__ import annotations

import copy
from pathlib import Path

import httpx
import pytest

from law_map import cli
from law_map import watch as watch_mod
from law_map.loader import load_corpus
from law_map.watch import (
    Instrument,
    format_watch_line,
    format_watch_summary,
    instruments_of,
    latest_egov_amendment,
    latest_eurlex_amendment,
    latest_uk_effect,
    watch_laws,
)

from .test_model import VALID_OBLIGATION, write_corpus

AI_ACT = Instrument("eurlex", "32024R1689")
UK_FEED = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:ukm="http://www.legislation.gov.uk/namespaces/metadata">
  <updated>2026-10-14T19:22:39+01:00</updated>
  <entry><updated>2026-02-13T10:22:58Z</updated>
    <content><ukm:Effect AffectingURI="http://www.legislation.gov.uk/id/uksi/2026/103"/></content></entry>
  <entry><updated>2024-12-17T11:18:29Z</updated>
    <content><ukm:Effect AffectingURI="http://www.legislation.gov.uk/id/uksi/2024/1124"/></content></entry>
</feed>"""


def _grounding(**over: object) -> dict:
    g = copy.deepcopy(VALID_OBLIGATION["groundings"][0])
    g.update(over)
    return g


def _corpus(tmp_path: Path, *groundings: dict):
    doc = copy.deepcopy(VALID_OBLIGATION)
    doc["groundings"] = list(groundings)
    return load_corpus(write_corpus(tmp_path, doc))


def test_instruments_from_urls_and_open_law_refs() -> None:
    g = _grounding(
        sources=[
            "https://eur-lex.europa.eu/eli/reg/2024/1689/oj",
            "https://eur-lex.europa.eu/eli/dir/2019/790/oj",
            "https://laws.e-gov.go.jp/document?lawid=415AC0000000057",
            "https://laws.e-gov.go.jp/law/345AC0000000048",
            "https://www.legislation.gov.uk/ukpga/1988/48/section/29A",
            "https://example.org/unrelated",
        ],
        open_law={"source": "eu", "id": "32024R1689"},
    )
    assert instruments_of(g) == [
        AI_ACT,
        Instrument("eurlex", "32019L0790"),
        Instrument("egov", "415AC0000000057"),
        Instrument("egov", "345AC0000000048"),
        Instrument("uk", "ukpga/1988/48"),
    ]


def test_parsers() -> None:
    eu = {
        "results": {
            "bindings": [
                {"celex": {"value": "32025R0001"}, "date": {"value": "2025-01-02"}},
                {"celex": {"value": "32026R1744"}, "date": {"value": "2026-07-08"}},
                {"celex": {"value": "32020R0001"}},
            ]
        }
    }
    assert latest_eurlex_amendment(eu) == ("2026-07-08", "CELEX 32026R1744")
    assert latest_eurlex_amendment({"results": {"bindings": []}}) is None
    egov = {
        "revisions": [
            {"amendment_promulgate_date": "2026-06-24", "amendment_law_num": "令和八年法律第四十六号"},
            {"amendment_promulgate_date": "2026-07-17", "amendment_law_num": "令和八年法律第五十六号"},
            {"amendment_promulgate_date": None},
        ]
    }
    assert latest_egov_amendment(egov) == ("2026-07-17", "令和八年法律第五十六号")
    assert latest_uk_effect(UK_FEED) == ("2026-02-13", "uksi/2026/103")
    with pytest.raises(ValueError):
        latest_uk_effect('<!DOCTYPE x [<!ENTITY a "a">]><feed/>')


def test_baselines_and_flags(tmp_path: Path) -> None:
    src = ["https://eur-lex.europa.eu/eli/reg/2024/1689/oj"]
    corpus = _corpus(
        tmp_path,
        _grounding(sources=src, effective="2024-08-01"),  # amended since effective
        _grounding(sources=src, effective="2024-08-01", reviewed_on="2026-10-15"),  # acknowledged
        _grounding(sources=src, status="scheduled", effective="2027-12-02"),  # no baseline
    )
    calls: list[Instrument] = []

    def fetch(instrument: Instrument):
        calls.append(instrument)
        return ("2026-07-08", "CELEX 32026R1744")

    probes = watch_laws(corpus, fetch=fetch)
    assert calls == [AI_ACT]  # fetched once, compared per grounding
    assert [p.problem for p in probes] == ["changed", None, "changed"]
    assert format_watch_line(probes[0]) == (
        "[law-watch changed] obligation.privacy.valid-fixture groundings[0] eurlex:32024R1689: "
        "amended 2026-07-08 by CELEX 32026R1744 (after effective 2024-08-01)"
    )
    assert format_watch_line(probes[1]) is None
    assert "no reviewed_on recorded" in str(format_watch_line(probes[2]))
    assert format_watch_summary(probes) == (
        "law-watch: 1 instrument(s), 2 grounding(s) changed, 0 not found, 0 unreachable"
    )


def test_fetch_failures(tmp_path: Path) -> None:
    corpus = _corpus(
        tmp_path,
        _grounding(sources=["https://laws.e-gov.go.jp/law/359AC0000000999"]),
        _grounding(sources=["https://www.legislation.gov.uk/ukpga/2018/12"]),
    )

    def fetch(instrument: Instrument):
        if instrument.kind == "egov":
            request = httpx.Request("GET", "https://laws.e-gov.go.jp/")
            raise httpx.HTTPStatusError("404", request=request, response=httpx.Response(404, request=request))
        raise httpx.ConnectError("down")

    probes = watch_laws(corpus, fetch=fetch)
    assert [p.problem for p in probes] == ["not-found", "unreachable"]
    assert str(format_watch_line(probes[0])).startswith("[law-watch not-found]")


def test_cli_watch_exit_code(tmp_path: Path, monkeypatch, capsys) -> None:
    doc = copy.deepcopy(VALID_OBLIGATION)
    doc["groundings"][0]["sources"] = ["https://eur-lex.europa.eu/eli/reg/2024/1689/oj"]
    root = write_corpus(tmp_path, doc)
    monkeypatch.setattr(watch_mod, "_http_fetch", lambda _client: lambda _i: ("2026-07-08", "CELEX x"))
    assert cli.main(["--root", str(root), "watch"]) == 1
    assert "[law-watch changed]" in capsys.readouterr().out
    monkeypatch.setattr(watch_mod, "_http_fetch", lambda _client: lambda _i: None)
    assert cli.main(["--root", str(root), "watch"]) == 0


def test_section_watch_refs_baseline_on_version(tmp_path: Path) -> None:
    from law_map.watch import collect_section_watch_refs

    refs = collect_section_watch_refs(
        [("region-eu-cra", ["https://eur-lex.europa.eu/eli/reg/2024/2847/oj"], "2026-09-21")]
    )
    assert len(refs) == 1
    assert refs[0].obligation_id == "region-eu-cra"
    assert refs[0].index == -1
    assert refs[0].baseline == "2026-09-21"
    assert refs[0].instrument == Instrument("eurlex", "32024R2847")


def test_watch_laws_covers_section_refs(tmp_path: Path) -> None:
    from law_map.watch import collect_section_watch_refs

    root = write_corpus(tmp_path, VALID_OBLIGATION)
    corpus = load_corpus(root)
    section_refs = collect_section_watch_refs(
        [("region-eu-cra", ["https://eur-lex.europa.eu/eli/reg/2024/2847/oj"], "2026-09-21")]
    )
    probes = watch_laws(corpus, fetch=lambda _i: ("2026-10-01", "CELEX x"), section_refs=section_refs)
    section_lines = [p for p in probes if p.ref.index == -1]
    assert len(section_lines) == 1
    line = format_watch_line(section_lines[0])
    assert line is not None and line.startswith("[law-watch changed] region-eu-cra section")
