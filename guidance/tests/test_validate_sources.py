"""Offline tests for the --sources liveness check in tools/validate.py.

Only pure helpers (URL collection, status classification, report
formatting) and the probe runner with a stubbed transport are exercised
here — no test touches the network.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import validate as v


@pytest.fixture
def sections_dir(tmp_path: Path) -> Path:
    root = tmp_path / "sections"
    (root / "baseline").mkdir(parents=True)
    (root / "lang").mkdir(parents=True)
    # Generated files are never scanned for sources.
    (root / "MANIFEST.yml").write_text(
        yaml.safe_dump({"sections": [{"id": "baseline-demo", "sources": ["https://example.com/manifest"]}]}),
        encoding="utf-8",
    )
    (root / "baseline" / "demo.md").write_text(
        "---\n"
        "id: baseline-demo\n"
        "sources:\n"
        "  - https://example.com/header\n"
        "  - https://example.com/shared\n"
        "---\n"
        "# Demo\n"
        "## 事実\n"
        "see https://example.com/body and https://example.com/shared.\n",
        encoding="utf-8",
    )
    (root / "lang" / "terms.yml").write_text(
        yaml.safe_dump(
            {
                "review_by": "2027-03-31",
                "terms": {
                    "jp": {"sources": ["https://example.com/yaml", "not-a-url"]},
                    "us": {"sources": [123, "ftp://example.com/nope"]},
                },
            }
        ),
        encoding="utf-8",
    )
    return root


def test_collect_covers_manifest_sections_and_yaml(sections_dir: Path) -> None:
    collected = v.collect_source_urls(sections_dir)
    assert "MANIFEST.yml" not in collected
    assert collected["baseline/demo.md"] == [
        "https://example.com/body",
        "https://example.com/header",
        "https://example.com/shared",
    ]
    assert collected["lang/terms.yml"] == ["https://example.com/yaml"]


def test_collect_dedups_shared_url_across_origins(sections_dir: Path) -> None:
    (sections_dir / "baseline" / "other.md").write_text(
        "---\nid: baseline-other\nsources: [https://example.com/shared]\n---\n"
        "body https://example.com/shared\n",
        encoding="utf-8",
    )
    calls: list[str] = []

    def probe(url: str) -> str:
        calls.append(url)
        return "200"

    probed, flagged = v.check_sources(sections_dir, probe=probe)
    assert probed == len(set(calls)) == 4
    assert flagged == []


def test_extract_section_urls_strips_trailing_punct() -> None:
    text = (
        '---\nid: x-y\nsources: ["https://example.com/a."]\n---\n'
        "see (https://example.com/b), https://example.com/c!\n"
    )
    assert v.extract_section_urls(text) == [
        "https://example.com/a",
        "https://example.com/b",
        "https://example.com/c",
    ]


def test_parse_curl_status_uses_final_response() -> None:
    code, locations = v.parse_curl_status(
        "HTTP/2 301\r\nlocation: https://example.com/new\r\n\r\nHTTP/2 200\r\n"
    )
    assert code == "200"
    assert locations == {"https://example.com/new"}


def test_curl_args_are_polite() -> None:
    args = v.curl_args("https://example.com/", True, 10.0, 2)
    assert "-I" in args
    assert args[args.index("-A") + 1].startswith("kanon-check/")
    assert args[args.index("--retry") + 1] == "2"
    assert args[args.index("--max-time") + 1] == "10"
    get_args = v.curl_args("https://example.com/", False, 10.0, 2)
    assert "-I" not in get_args
    assert "-o" in get_args


def _runner_factory(responses: list[tuple[str, int]]) -> types.SimpleNamespace:
    calls: list[list[str]] = []
    queue = list(responses)

    def runner(cmd: list[str], **kwargs: object) -> types.SimpleNamespace:
        calls.append(cmd)
        body, code = queue.pop(0)
        return types.SimpleNamespace(stdout=body, returncode=code)

    return types.SimpleNamespace(runner=runner, calls=calls)


def test_probe_source_head_ok() -> None:
    stub = _runner_factory([("HTTP/2 200\r\n\r\n", 0)])
    assert v.probe_source("https://example.com/", runner=stub.runner) == "200"
    assert len(stub.calls) == 1
    assert "-I" in stub.calls[0]


def test_probe_source_falls_back_to_get_on_405() -> None:
    stub = _runner_factory(
        [("HTTP/1.1 405 Method Not Allowed\r\n\r\n", 0), ("HTTP/1.1 200 OK\r\n\r\n", 0)]
    )
    assert v.probe_source("https://example.com/", runner=stub.runner) == "200"
    assert len(stub.calls) == 2
    assert "-I" not in stub.calls[1]


def test_probe_source_reports_redirect_target() -> None:
    stub = _runner_factory(
        [("HTTP/2 301\r\nlocation: https://example.com/new\r\n\r\n", 0)]
    )
    assert "https://example.com/new" in v.probe_source(
        "https://example.com/", runner=stub.runner
    )


def test_is_flagged_status() -> None:
    assert v.is_flagged_status("404")
    assert v.is_flagged_status("503")
    assert v.is_flagged_status("no HTTP status (exit 28)")
    assert v.is_flagged_status("curl unavailable")
    assert not v.is_flagged_status("200")
    assert not v.is_flagged_status("301 -> https://example.com/new")


def test_format_source_summary() -> None:
    assert v.format_source_summary(59, 0) == "[drift] source probes: 59 total, 0 flagged"
    assert v.format_source_summary(59, 3) == "[drift] source probes: 59 total, 3 flagged"


def test_run_sources_check_exit_codes(sections_dir: Path, capsys) -> None:
    assert v.run_sources_check(sections_dir, probe=lambda url: "200") == 0
    assert "0 flagged" in capsys.readouterr().out

    def flaky(url: str) -> str:
        return "404" if url.endswith("/shared") else "200"

    assert v.run_sources_check(sections_dir, probe=flaky) == 1
    out = capsys.readouterr().out
    assert "<-- FLAGGED" in out
    assert "1 flagged" in out


def test_check_upstream_project_status_correlates_law_map(tmp_path: Path) -> None:
    law_map_dir = tmp_path / "law-map"
    open_law_dir = tmp_path / "open-law"
    ob_dir = law_map_dir / "obligations" / "security"
    ob_dir.mkdir(parents=True)
    (ob_dir / "test-vdp.yml").write_text(
        yaml.safe_dump(
            {
                "id": "obligation.security.vdp",
                "title": "VDP policy",
                "related_sections": ["baseline-vdp"],
                "groundings": [
                    {
                        "authority": "CISA BOD 20-01",
                        "status": "in_force",
                        "review_by": "2027-03-31",
                        "sources": ["https://example.com/cisa"],
                        "open_law": {"source": "us", "id": "bod-20-01"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    notes = v.check_upstream_project_status(
        "baseline/vdp.md",
        "https://example.com/cisa",
        law_map_dir=law_map_dir,
        open_law_dir=open_law_dir,
    )
    assert any("obligation.security.vdp" in n for n in notes)
    assert any("CISA BOD 20-01" in n for n in notes)
    assert any("2027-03-31" in n for n in notes)
