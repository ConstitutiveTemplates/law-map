"""Export obligations as guidance-format section drafts (``.md`` skeletons).

Each obligation becomes one ``<slug>.md`` file whose YAML front matter
mirrors a real ``guidance/sections`` entry (``id``, ``version``,
``status``, ``placement``, ``when``, ``obligations``, ``triggers``,
``sources``, ``license``, ``en``) so the draft passes the section
validators once copied to ``guidance/sections/draft/<slug>.md``. The body
keeps the 事実 / 禁止パターン / 推奨設定 / 運用チェック / 制度変更ウォッチ
skeleton: groundings, citations, URLs and the review-by wiring are filled
in mechanically; the prose sections are placeholders that humans flesh out
later. Deterministic and offline.

The ``when`` conditions come from a scope/category mapping onto the
``guidance/sections/VOCABULARY.yml`` terms (falling back to ``always``).
``triggers.pattern`` (plus ``config`` when a second pattern exists) comes
from the obligation's check-spec ``triggers`` when ``checks_root`` is given
and a referenced spec parses, otherwise from the scope keywords.

Only ``render_obligation`` and ``export_obligations`` are public; the rest
are single-purpose section builders.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from .model import Obligation, obligation_groundings

GUIDANCE_LICENSE = "CC-BY-4.0"
_LICENSE_NOTE = (
    "<!-- © kanon contributors (https://github.com/politeuma/kanon). "
    "Section {id}, licensed CC BY 4.0: https://creativecommons.org/licenses/by/4.0/ -->"
)

_PLACEHOLDER_HEADINGS = ("禁止パターン", "推奨設定", "運用チェック")

# Scope components -> guidance `when` terms (guidance/sections/VOCABULARY.yml).
_COMPONENT_WHEN: dict[str, str] = {
    # Biometric identification.
    "face_recognition": "face_recognition",
    "liveness": "face_recognition",
    "embedding_store": "face_recognition",
    "attribute_classification": "face_recognition",
    # Medical / SaMD software.
    "clinical_algorithm": "medtech",
    "diagnostic_model": "medtech",
    "screening_pipeline": "medtech",
    "inference_engine": "medtech",
    # Copyright training-data use and dataset work.
    "scraping": "scraping",
    "dataset_provenance": "data_science",
    "data_pipeline": "data_science",
    "model_training": "data_science",
    "evaluation_pipeline": "data_science",
    "scoring_service": "data_science",
    # Agentic / LLM tool use.
    "llm_client": "mcp",
    "tool_call": "mcp",
    "tool_execution": "mcp",
    "agent_loop": "mcp",
    "mcp_server": "mcp",
    "prompt_template": "mcp",
    "prompt_builder": "mcp",
    "rag_pipeline": "mcp",
    # Online-judge and data-competition code.
    "solution_scaffold": "oj_code",
    "contest_submission": "oj_code",
    "judge_client": "oj_code",
    # Embedded / firmware networking.
    "ntp_client": "embedded",
    "time_synchronization": "embedded",
    "firmware_network": "embedded",
    "embedded_iot": "embedded",
}

# Scope data types -> guidance `when` terms.
_DATA_TYPE_WHEN: dict[str, str] = {
    "face_image": "face_recognition",
    "biometric_identifier": "face_recognition",
    "embedding": "face_recognition",
    "medical_images": "medtech",
    "patient_records": "medtech",
    "diagnostic_telemetry": "medtech",
    "problem_statement": "oj_code",
    "source_code": "oj_code",
    "test_cases": "oj_code",
    "prompt": "mcp",
    "tool_output": "mcp",
    "model_output": "mcp",
    "retrieved_document": "mcp",
    "untrusted_input": "mcp",
    "copyrighted_text": "data_science",
    "copyrighted_media": "data_science",
    "dataset_metadata": "data_science",
    "demographic_data": "data_science",
    "feature_vector": "data_science",
    "prediction": "data_science",
    "personal_data": "personal_data",
    "email": "personal_data",
    "phone": "personal_data",
    "person_name": "personal_data",
    "ip_address": "personal_data",
    "government_id": "personal_data",
    "identifier": "personal_data",
    "device_id": "personal_data",
    "browsing_data": "personal_data",
}

# Category -> guidance `when` terms; used only when the scope yields nothing.
_CATEGORY_WHEN: dict[str, list[str]] = {
    "privacy": ["personal_data"],
    "accessibility": ["eu_market"],
    "copyright": ["scraping", "data_science"],
    "ai": ["ai_assisted"],
    "licensing": ["commercial"],
}

__all__ = ["export_obligations", "render_obligation"]


def render_obligation(
    ob: Obligation,
    today: date | None = None,
    checks_root: str | Path | None = None,
) -> str:
    """Render one obligation as a guidance-format section draft."""
    slug = _obligation_slug(ob)
    section_id = f"draft-{slug}"
    title = str(ob.data.get("title") or ob.id)
    summary = _collapse(ob.data.get("summary")) or title
    front: dict[str, Any] = {
        "id": section_id,
        "version": f"{(today or date.today()).isoformat()}.1",
        "status": "draft",
        "placement": "agents_md",
        "when": _section_when(ob),
        "obligations": [ob.id],
        "triggers": _section_triggers(ob, checks_root),
        "sources": _section_sources(ob),
        "license": GUIDANCE_LICENSE,
        "en": _section_en(ob, title, summary),
    }
    front_text = "---\n" + _dump_front_matter(front) + "---\n"
    lines: list[str] = [f"# {title}", "", f"> 要約: {summary}", ""]
    scope_line = _scope_line(ob)
    if scope_line is not None:
        lines += [scope_line, ""]
    lines.extend(_directive_section(_obligation_directives(ob), _enforcement_summary(ob)))
    _append_block(lines, "## 事実")
    for i, g in enumerate(obligation_groundings(ob), 1):
        lines.extend(_grounding_section(g, i))
    for heading in _PLACEHOLDER_HEADINGS:
        _append_block(
            lines,
            f"## {heading}",
            "<!-- TODO: flesh out with implementation detail grounded in 事実 above. -->",
        )
    lines.extend(_review_watch_section(ob))
    lines.append(_LICENSE_NOTE.format(id=section_id))
    return front_text + "\n".join(lines) + "\n"


def export_obligations(
    obligations: list[Obligation],
    out_dir: str | Path,
    today: date | None = None,
    checks_root: str | Path | None = None,
) -> list[Path]:
    """Write one ``.md`` guidance draft per obligation into ``out_dir``; return written paths."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for ob in sorted(obligations, key=lambda o: o.id):
        target = out / f"{_obligation_slug(ob)}.md"
        target.write_text(render_obligation(ob, today=today, checks_root=checks_root), encoding="utf-8")
        written.append(target)
    return written


def _obligation_slug(ob: Obligation) -> str:
    return ob.id.rsplit(".", 1)[-1]


class _FrontDumper(yaml.SafeDumper):
    """Section-style YAML: scalar lists flow (``[a, b]``), strings single-quoted where needed."""


def _represent_front_str(dumper: yaml.SafeDumper, data: str) -> yaml.Node:
    style = None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}\.\d+", data):
        style = '"'
    elif "\\" in data or re.search(r": |^https?://|['\"]", data) or data != data.strip():
        style = "'"
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)


def _represent_front_list(dumper: yaml.SafeDumper, data: list[Any]) -> yaml.Node:
    flow = all(not isinstance(item, (dict, list)) for item in data)
    return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=flow)


_FrontDumper.add_representer(str, _represent_front_str)
_FrontDumper.add_representer(list, _represent_front_list)


def _dump_front_matter(front: dict[str, Any]) -> str:
    """Dump the front mapping the way real sections write it (quoted version, flow lists)."""
    return yaml.dump(front, Dumper=_FrontDumper, sort_keys=False, allow_unicode=True, width=10_000)


def _collapse(value: object) -> str:
    """Collapse whitespace runs to single spaces; ``""`` for non-strings."""
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())


def _section_when(ob: Obligation) -> list[str]:
    """Guidance ``when`` terms from scope components/data types, else category, else ``always``."""
    seen: list[str] = []

    def add(term: str | None) -> None:
        if term is not None and term not in seen:
            seen.append(term)

    scope = ob.data.get("scope")
    if isinstance(scope, dict):
        components = scope.get("components")
        if isinstance(components, list):
            for component in components:
                add(_COMPONENT_WHEN.get(str(component)))
        data_types = scope.get("data_types")
        if isinstance(data_types, list):
            for data_type in data_types:
                add(_DATA_TYPE_WHEN.get(str(data_type)))
    if not seen:
        for term in _CATEGORY_WHEN.get(str(ob.data.get("category")), []):
            add(term)
    return seen or ["always"]


def _section_keywords(ob: Obligation) -> list[str]:
    """Presence-scan keywords from scope components plus category/modality."""
    keywords: list[str] = []
    scope = ob.data.get("scope")
    if isinstance(scope, dict) and isinstance(scope.get("components"), list):
        keywords.extend(str(c) for c in scope["components"] if str(c).strip())
    for key in ("category", "modality"):
        value = ob.data.get(key)
        if isinstance(value, str) and value.strip():
            keywords.append(value)
    return keywords or [_obligation_slug(ob)]


def _section_triggers(ob: Obligation, checks_root: str | Path | None) -> dict[str, Any]:
    """Guidance ``triggers`` mapping: keywords plus pattern/config regexes.

    The regexes come from the obligation's check-spec ``triggers`` when a
    referenced spec parses; otherwise the pattern is built from the scope
    keywords and ``config`` is omitted for the human to fill in.
    """
    keywords = _section_keywords(ob)
    patterns = _spec_trigger_patterns(ob, checks_root) if checks_root is not None else []
    if patterns:
        triggers: dict[str, Any] = {"keywords": keywords, "pattern": patterns[0]}
        if len(patterns) > 1:
            triggers["config"] = patterns[1]
        return triggers
    fallback = "(?i)\\b(" + "|".join(re.escape(k) for k in keywords) + ")\\b"
    return {"keywords": keywords, "pattern": fallback}


def _spec_trigger_patterns(ob: Obligation, checks_root: str | Path) -> list[str]:
    """Check-spec trigger regexes for the first referenced spec that parses."""
    enforcement = ob.data.get("enforcement")
    refs = enforcement.get("check_refs") if isinstance(enforcement, dict) else None
    if not isinstance(refs, list):
        return []
    root = Path(checks_root)
    for ref in sorted(str(r) for r in refs):
        try:
            data = yaml.safe_load((root / f"{ref}.yml").read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue
        if not isinstance(data, dict) or not isinstance(data.get("triggers"), list):
            continue
        patterns = [t for t in data["triggers"] if isinstance(t, str) and t.strip()]
        if not patterns:
            continue
        try:
            for pattern in patterns:
                re.compile(pattern)
        except re.error:
            continue
        return patterns
    return []


def _section_sources(ob: Obligation) -> list[str]:
    """Deduplicated grounding source URLs (primary citations the draft rests on)."""
    urls: list[str] = []
    for g in obligation_groundings(ob):
        sources = g.get("sources")
        if not isinstance(sources, list):
            continue
        for url in sources:
            if isinstance(url, str) and url.startswith(("http://", "https://")) and url not in urls:
                urls.append(url)
    return urls


def _section_en(ob: Obligation, title: str, summary: str) -> dict[str, Any]:
    """Concise English rendering: summary (+ human directive) and prohibited (agent directive)."""
    directives = _obligation_directives(ob)
    summary_list = [summary]
    human = directives.get("human")
    if human and human != summary:
        summary_list.append(human)
    agent = directives.get("agent")
    return {"title": title, "summary": summary_list, "prohibited": [agent] if agent else [summary]}


def _scope_line(ob: Obligation) -> str | None:
    """One-line 適用条件 quote from the scope components, if any."""
    scope = ob.data.get("scope")
    if not isinstance(scope, dict) or not isinstance(scope.get("components"), list):
        return None
    components = [str(c) for c in scope["components"] if str(c).strip()]
    if not components:
        return None
    return f"> **適用条件**: {', '.join(components)} を扱う場面(草案: 本文で具体化する)。"


def _obligation_directives(ob: Obligation) -> dict[str, str]:
    """Obligation directives (human/agent) as plain strings."""
    raw = ob.data.get("directives")
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for key in ("human", "agent"):
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            out[key] = " ".join(value.split())
    return out


def _enforcement_summary(ob: Obligation) -> str | None:
    """One-line enforcement wiring (level + check_refs) for the skeleton."""
    enforcement = ob.data.get("enforcement")
    if not isinstance(enforcement, dict):
        return None
    parts: list[str] = []
    if isinstance(enforcement.get("level"), str) and enforcement["level"]:
        parts.append(f"level={enforcement['level']}")
    refs = enforcement.get("check_refs")
    if isinstance(refs, list) and refs:
        parts.append("check_refs=[" + ", ".join(f"checks/{r}.yml" for r in refs) + "]")
    return " ".join(parts) or None


def _append_block(lines: list[str], *blocks: str) -> None:
    """Append markdown blocks separated by exactly one blank line each."""
    for block in blocks:
        lines.append(block)
        lines.append("")


def _directive_section(directives: dict[str, str], enforcement_line: str | None) -> list[str]:
    """The optional ``## Directives`` section (empty when there is nothing to show)."""
    if not directives and not enforcement_line:
        return []
    lines = ["## Directives", ""]
    for key in ("human", "agent"):
        if key in directives:
            lines.append(f"- {key}: {directives[key]}")
    if enforcement_line:
        lines.append(f"- enforcement: {enforcement_line}")
    lines.append("")
    return lines


def _grounding_section(g: dict[str, Any], index: int) -> Iterator[str]:
    jurisdiction = g.get("jurisdiction", "?")
    if g.get("subdivision"):
        jurisdiction = f"{jurisdiction}-{g['subdivision']}"
    yield f"### {index}. {jurisdiction} — {g.get('source_type', '?')} ({g.get('status', '?')})"
    yield ""
    yield f"- authority: {_collapse(g.get('authority')) or '—'}"
    yield f"- citation: {_collapse(g.get('citation')) or '—'}"
    if _collapse(g.get("effective")):
        yield f"- effective: {_collapse(g.get('effective'))}"
    if _collapse(g.get("applicability")):
        yield f"- applicability: {_collapse(g.get('applicability'))}"
    sources = g.get("sources", [])
    if isinstance(sources, list):
        for url in sources:
            yield f"- source: {url}"
    yield ""


def _review_watch_section(ob: Obligation) -> list[str]:
    lines = [
        "## 制度変更ウォッチ",
        "",
        "<!-- 確認TODO: re-review every grounding on its review_by date. -->",
    ]
    for i, g in enumerate(obligation_groundings(ob), 1):
        lines.append(f"- 確認TODO: {g.get('jurisdiction', '?')} grounding #{i}: review_by {g.get('review_by', '?')}")
    lines += [
        "",
        "<!--",
        "本セクションは法的助言を構成しません。規制状況は変化します。",
        "→ https://github.com/politeuma/law-map (義務グラフの原本)",
        "-->",
        "",
    ]
    return lines
