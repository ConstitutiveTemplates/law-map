"""Shared paths, vocabularies, patterns, and probe constants."""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

ProbeFn = Callable[[str], str]
RunnerFn = Callable[..., Any]

REPO = Path(__file__).resolve().parent.parent.parent
SECTIONS = REPO / "sections"
MANIFEST = SECTIONS / "MANIFEST.yml"
VOCABULARY = SECTIONS / "VOCABULARY.yml"
LICENSE_FILE = SECTIONS / "LICENSE"
# Files whose vocabulary tables tools/manifest.py regenerates.
GENERATED_DOCS = (REPO / "README.md", REPO / "CONTRIBUTING.md")

# --- Front matter contract --------------------------------------------------
# The when / placement / status vocabularies live in sections/VOCABULARY.yml
# (see :mod:`validation.vocabulary`); MANIFEST.yml is generated from the
# section front matter plus that file (see :mod:`validation.manifest`).
REQUIRED_HEADINGS = ("## 事実", "## 禁止パターン", "## 推奨設定", "## 運用チェック", "## 制度変更ウォッチ")

# sections/<tier>/<slug>.md -- _template.md at the top level is an
# authoring aid, not a section, and is deliberately not matched.
SECTION_SUFFIX = ".md"
SECTION_GLOB = f"*/*{SECTION_SUFFIX}"

FRONT_MATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
FRONT_MATTER_KEYS = (
    "id", "version", "status", "placement", "when", "obligations",
    "triggers", "sources", "license", "en",
)
TRIGGER_KEYS = ("keywords", "pattern", "config")
EN_KEYS = ("title", "summary", "prohibited")
VERSION_RE = re.compile(r"\d{4}-\d{2}-\d{2}\.\d+")
OBLIGATION_ID_RE = re.compile(r"obligation\.[a-z0-9-]+\.[a-z0-9-]+")
# Section prose is CC BY 4.0 (sections/LICENSE); code stays Apache-2.0.
SECTION_LICENSE = "CC-BY-4.0"
SECTION_LICENSE_HEAD = "Attribution 4.0 International"
# Per-section attribution note: the last line of every body, so the credit
# and license link travel with the prose when a consumer pastes it.
LICENSE_NOTE = (
    "<!-- © kanon contributors (https://github.com/politeuma/kanon). "
    "Section {id}, licensed CC BY 4.0: https://creativecommons.org/licenses/by/4.0/ -->"
)

# --- Section body patterns --------------------------------------------------
REVIEW_BY_RE = re.compile(r"review_by:\s*(\d{4}-\d{2}-\d{2})")
URL_RE = re.compile(r"https?://[^\s)<>\]\"']+")
JINJA_RE = re.compile(r"\{\{|\{%")
REVIEW_HORIZON = dt.timedelta(days=30)

# Phrases a section (body or en: block) must never contain: consumer
# internals (kanon is consumer-agnostic), metadata that belongs in front
# matter, and retired project names. (pattern, reason) pairs.
BANNED_PHRASES: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(pattern, flags), reason)
    for pattern, flags, reason in (
        (r"REGISTRY\.ya?ml", 0, "consumer registry file"),
        (r"_shared/", 0, "consumer template path"),
        (r"copier", re.IGNORECASE, "consumer template engine"),
        (r"\bQA\s*L[0-3]\b", 0, "consumer QA level"),
        (r"test_ethics_registry", 0, "consumer test name"),
        (r"\barchitekton", re.IGNORECASE, "consumer name"),
        (r"\bdaimonion\b", re.IGNORECASE, "consumer name"),
        (r"\w+_effective\b", 0, "consumer flag name"),
        (r"^> *配布:|配布: *(library|cli|web|mcp|kaggle|data-science|IoT)", re.MULTILINE,
         "distribution line (the front matter `when` carries it)"),
        (r"^> *Triggers:", re.MULTILINE, "Triggers line (the front matter `triggers` carries it)"),
        (r"設定側トリガー\(\s*Copier", 0, "consumer QA trigger"),
        (
            "|".join((r"ConstitutiveTemplates", r"python-copier-template", r"good-future-codex",
                      r"\bcodex\b", r"\bfoundry\b", r"law-lint", r"\borimono\b", r"kasi-x")),
            re.IGNORECASE,
            "retired project name",
        ),
    )
)

# --- Declared-source liveness probing ---------------------------------------
SOURCE_TIMEOUT = 10.0
SOURCE_RETRIES = 2
SOURCE_USER_AGENT = (
    "kanon-check/1.0"
    " (+https://github.com/politeuma/kanon)"
)
CURL_STATUS_RE = re.compile(r"^http/\S+\s+(\d{3})\b", re.IGNORECASE)

# HTTP status classes treated as dead/flagged probe results.
FLAGGED_STATUS_PREFIXES = ("40", "50")
# Markers of non-HTTP probe results (curl missing, no response received).
NO_HTTP_STATUS_MARKER = "no HTTP status"
UNAVAILABLE_MARKER = "unavailable"
# HEAD responses retried as GET (server refuses HEAD but may serve GET).
HEAD_FALLBACK_CODES = frozenset({"405", "501"})
# Redirect responses carry a target location worth reporting.
REDIRECT_STATUS_PREFIX = "30"
# Upstream grounding lookup locations.
OBLIGATIONS_SUBDIR = "obligations"
OPEN_LAW_SOURCES_SUBDIR = Path("src") / "open_law" / "sources"

# Probe-result triple: (origin relpath, url, status string).
SourceFlag = tuple[str, str, str]

# Process-global validation message sinks (shared with report helpers and
# the legacy ``validate`` shim).
errors: list[str] = []
warnings: list[str] = []
