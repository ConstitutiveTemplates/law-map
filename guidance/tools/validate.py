#!/usr/bin/env python3
"""Validate the kanon sections corpus.

Section shape (sections/<tier>/<slug>.md):

    ---
    id: <tier>-<slug>
    version: "YYYY-MM-DD.rev"
    status: draft | active
    placement: agents_md | charter | legal_md | standalone
    when: <condition> | [<condition>, ...]      # sections/VOCABULARY.yml
    obligations: [obligation.<category>.<slug>, ...]   # law-map ids
    triggers: {keywords: [...], pattern: '<regex>', config: '<regex>'}
    sources: [https://..., ...]
    license: CC-BY-4.0
    en: {title: ..., summary: [...], prohibited: [...]}
    ---
    # <title>
    > **適用条件**: ...
    ## 事実 ... ## 禁止パターン ... ## 推奨設定 ... ## 運用チェック ...
    ## 制度変更ウォッチ  (may contain (review_by: YYYY-MM-DD) dates)

Checks (all errors are collected; exit 1 if any, else 0):

  * every file opens with YAML front matter carrying exactly the keys above;
    id equals ``<tier>-<slug>`` from the path; version/status/placement/when
    stay in the vocabulary; trigger regexes compile; en has a title and
    non-empty summary/prohibited lists
  * bodies are consumer-agnostic: no ``{{`` / ``{%`` template expressions and
    no banned phrases (consumer internals, distribution/Triggers lines that
    belong in front matter, retired project names)
  * every section keeps the required headings in order
    (## 事実 / ## 禁止パターン / ## 推奨設定 / ## 運用チェック / ## 制度変更ウォッチ)
  * review_by dates that are present must not be expired (due < 30d warns);
    a section with no law-map ``obligations`` must carry at least one
  * section ids are unique
  * sections/MANIFEST.yml and the README/CONTRIBUTING vocabulary tables
    match what tools/manifest.py generates

Run:  uv run --with pyyaml python tools/validate.py
      uv run --with pyyaml python tools/validate.py --drift
      uv run --with pyyaml python tools/validate.py --sources
      (--drift prints due/expired review_by + probes declared source URLs
      with curl HEAD (GET fallback) and never exits non-zero; --sources
      probes only the declared source URLs and exits 1 when any is flagged)

Implementation lives in :mod:`validation` (split by responsibility);
this module keeps the historical ``python tools/validate.py`` entry point
and the ``import validate`` attribute surface working.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from validation.cli import main, print_validation_report
from validation.const import (
    BANNED_PHRASES,
    CURL_STATUS_RE,
    FLAGGED_STATUS_PREFIXES,
    FRONT_MATTER_KEYS,
    FRONT_MATTER_RE,
    HEAD_FALLBACK_CODES,
    JINJA_RE,
    LICENSE_FILE,
    LICENSE_NOTE,
    MANIFEST,
    NO_HTTP_STATUS_MARKER,
    OBLIGATIONS_SUBDIR,
    OPEN_LAW_SOURCES_SUBDIR,
    REDIRECT_STATUS_PREFIX,
    REPO,
    REQUIRED_HEADINGS,
    REVIEW_BY_RE,
    REVIEW_HORIZON,
    SECTIONS,
    SECTION_GLOB,
    SECTION_LICENSE,
    SOURCE_RETRIES,
    SOURCE_TIMEOUT,
    SOURCE_USER_AGENT,
    UNAVAILABLE_MARKER,
    URL_RE,
    VOCABULARY,
    ProbeFn,
    RunnerFn,
    SourceFlag,
    errors,
    warnings,
)
from validation.corpus import (
    check_banned_phrases,
    check_flag_agnostic,
    check_front_matter,
    check_headings,
    check_license_file,
    check_license_note,
    check_review_by,
    expected_id,
    section_files,
    validate_corpus,
    validate_section_files,
)
from validation.frontmatter import read_section, split_front_matter
from validation.manifest import build_manifest, render_manifest
from validation.vocabulary import load_vocabulary, when_vocab
from validation.liveness import (
    check_sources,
    drift_report,
    flagged_unique_count,
    format_source_summary,
    is_flagged_status,
    print_source_summary,
    run_sources_check,
)
from validation.probe import curl_args, parse_curl_status, probe_source
from validation.report import error, reset, warn
from validation.sources import (
    collect_source_urls,
    extract_section_urls,
    extract_yaml_sources,
    strip_url_punct,
)
from validation.upstream import check_upstream_project_status

__all__ = [
    "BANNED_PHRASES",
    "CURL_STATUS_RE",
    "FLAGGED_STATUS_PREFIXES",
    "FRONT_MATTER_KEYS",
    "FRONT_MATTER_RE",
    "HEAD_FALLBACK_CODES",
    "JINJA_RE",
    "LICENSE_FILE",
    "LICENSE_NOTE",
    "MANIFEST",
    "NO_HTTP_STATUS_MARKER",
    "OBLIGATIONS_SUBDIR",
    "OPEN_LAW_SOURCES_SUBDIR",
    "ProbeFn",
    "REDIRECT_STATUS_PREFIX",
    "REPO",
    "REQUIRED_HEADINGS",
    "REVIEW_BY_RE",
    "REVIEW_HORIZON",
    "RunnerFn",
    "SECTIONS",
    "SECTION_GLOB",
    "SECTION_LICENSE",
    "SOURCE_RETRIES",
    "SOURCE_TIMEOUT",
    "SOURCE_USER_AGENT",
    "SourceFlag",
    "UNAVAILABLE_MARKER",
    "URL_RE",
    "VOCABULARY",
    "check_banned_phrases",
    "check_flag_agnostic",
    "check_front_matter",
    "check_headings",
    "check_license_file",
    "check_license_note",
    "check_review_by",
    "check_sources",
    "collect_source_urls",
    "drift_report",
    "errors",
    "expected_id",
    "extract_section_urls",
    "extract_yaml_sources",
    "flagged_unique_count",
    "format_source_summary",
    "is_flagged_status",
    "print_source_summary",
    "run_sources_check",
    "section_files",
    "strip_url_punct",
    "validate_corpus",
    "validate_section_files",
    "warnings",
]

# Back-compat: the pre-split module exposed these private helpers, so keep
# them importable (without advertising them in __all__).
from validation.corpus import _validate_section_file  # noqa: E402
from validation.liveness import (  # noqa: E402
    _format_source_line,
    _is_flagged_with_grounding,
    _print_upstream_notes,
    _probe_unique_urls,
    _report_review_dates_drift,
    _report_source_liveness,
)
from validation.probe import _run_curl  # noqa: E402
from validation.sources import (  # noqa: E402
    _add_source_urls,
    _collect_yaml_source_urls,
    _section_file_source_urls,
    _split_front_matter_sources,
    _yaml_data_source_urls,
)
from validation.upstream import (  # noqa: E402
    _load_obligation_doc,
    _obligation_notes,
    _open_law_note,
)

# Back-compat: the old module printed via a private `_print_validation_report`.
_print_validation_report = print_validation_report


if __name__ == "__main__":
    sys.exit(main())
