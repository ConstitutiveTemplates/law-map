"""Export obligations to good-future-codex-style ``.md.jinja`` section skeletons.

Each obligation becomes one file named after its id slug. The output is a
skeleton: structure, groundings, citations, URLs and the review-by wiring
are filled in mechanically; the prose sections are placeholders that humans
flesh out later. Deterministic and offline.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Any

from .model import Obligation, obligation_groundings

_VERSION_TODAY = date.today()
_PLACEHOLDER_HEADINGS = ("禁止パターン", "推奨設定", "運用チェック")


def _slug(ob: Obligation) -> str:
    return ob.id.rsplit(".", 1)[-1]


def _version_date(today: date | None = None) -> str:
    return (today or _VERSION_TODAY).isoformat()


def _triggers(ob: Obligation) -> list[str]:
    triggers: list[str] = []
    scope = ob.data.get("scope")
    if isinstance(scope, dict) and isinstance(scope.get("components"), list):
        triggers.extend(str(c) for c in scope["components"])
    for key in ("category", "modality"):
        value = ob.data.get(key)
        if isinstance(value, str):
            triggers.append(value)
    return triggers or ["general"]


def _directives(ob: Obligation) -> dict[str, str]:
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


def _enforcement_line(ob: Obligation) -> str | None:
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


def _append(lines: list[str], *blocks: str) -> None:
    """Append markdown blocks separated by exactly one blank line each."""
    for block in blocks:
        lines.append(block)
        lines.append("")


def _directive_lines(directives: dict[str, str], enforcement_line: str | None) -> list[str]:
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


def _grounding_lines(g: dict[str, Any], index: int) -> Iterator[str]:
    jurisdiction = g.get("jurisdiction", "?")
    if g.get("subdivision"):
        jurisdiction = f"{jurisdiction}-{g['subdivision']}"
    yield f"### {index}. {jurisdiction} — {g.get('source_type', '?')} ({g.get('status', '?')})"
    yield ""
    yield f"- authority: {g.get('authority', '—')}"
    yield f"- citation: {g.get('citation', '—')}"
    for key in ("effective", "applicability"):
        if g.get(key):
            yield f"- {key}: {g[key]}" if key == "effective" else f"- {key}: {str(g[key]).strip()}"
    for url in g.get("sources", []):
        yield f"- source: {url}"
    yield ""


def render_obligation(ob: Obligation, today: date | None = None) -> str:
    """Render one obligation as a ``.md.jinja`` codex section skeleton."""
    slug = _slug(ob)
    version = _version_date(today)
    triggers = ", ".join(_triggers(ob))
    lines: list[str] = []
    _append(
        lines,
        f"{{# ethics: id={slug} version={version}.1 status=draft triggers=[{triggers}] #}}",
        f"# {ob.data.get('title', ob.id)}",
        f"> 要約: {ob.data.get('summary', '').strip()}",
    )
    lines.extend(_directive_lines(_directives(ob), _enforcement_line(ob)))
    _append(lines, "## 事実")
    for i, g in enumerate(obligation_groundings(ob), 1):
        lines.extend(_grounding_lines(g, i))
    for heading in _PLACEHOLDER_HEADINGS:
        _append(
            lines,
            f"## {heading}",
            "<!-- TODO: flesh out with implementation detail grounded in 事実 above. -->",
        )
    lines.append("## 制度変更ウォッチ")
    lines.append("")
    lines.append("<!-- 確認TODO: re-review every grounding on its review_by date. -->")
    for i, g in enumerate(obligation_groundings(ob), 1):
        lines.append(f"- 確認TODO: {g.get('jurisdiction', '?')} grounding #{i}: review_by {g.get('review_by', '?')}")
    lines.append("")
    lines.append("<!--")
    lines.append("本セクションは法的助言を構成しません。規制状況は変化します。")
    lines.append("→ https://github.com/ConstitutiveTemplates/law-map (義務グラフの原本)")
    lines.append("-->")
    lines.append("")
    return "\n".join(lines)


def export_obligations(
    obligations: list[Obligation], out_dir: str | Path, today: date | None = None
) -> list[Path]:
    """Write one ``.md.jinja`` per obligation into ``out_dir``; return written paths.

    ``today`` is the version date stamp; defaulting to import-time
    ``_VERSION_TODAY`` when omitted keeps direct callers' behavior identical.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for ob in sorted(obligations, key=lambda o: o.id):
        target = out / f"{_slug(ob)}.md.jinja"
        target.write_text(render_obligation(ob, today=today), encoding="utf-8")
        written.append(target)
    return written
