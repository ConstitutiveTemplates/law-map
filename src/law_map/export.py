"""Export obligations to good-future-codex-style ``.md.jinja`` section skeletons.

Each obligation becomes one file named after its id slug. The output is a
skeleton: structure, groundings, citations, URLs and the review-by wiring
are filled in mechanically; the prose sections are placeholders that humans
flesh out later. Deterministic and offline.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from .model import Obligation

YEAR_0 = date(1970, 1, 1)
_VERSION_TODAY = date.today()


def _slug(ob: Obligation) -> str:
    return ob.id.rsplit(".", 1)[-1]


def _version_date(today: date | None = None) -> str:
    return (today or _VERSION_TODAY).isoformat()


def _triggers(ob: Obligation) -> list[str]:
    triggers: list[str] = []
    scope = ob.data.get("scope")
    if isinstance(scope, dict) and isinstance(scope.get("components"), list):
        triggers.extend(str(c) for c in scope["components"])
    category = ob.data.get("category")
    if isinstance(category, str):
        triggers.append(category)
    modality = ob.data.get("modality")
    if isinstance(modality, str):
        triggers.append(modality)
    return triggers or ["general"]


def render_obligation(ob: Obligation, today: date | None = None) -> str:
    """Render one obligation as a ``.md.jinja`` codex section skeleton."""
    slug = _slug(ob)
    version = _version_date(today)
    triggers = ", ".join(_triggers(ob))
    lines: list[str] = []
    lines.append(f"{{# ethics: id={slug} version={version}.1 status=draft triggers=[{triggers}] #}}")
    lines.append("")
    lines.append(f"# {ob.data.get('title', ob.id)}")
    lines.append("")
    lines.append(f"> 要約: {ob.data.get('summary', '').strip()}")
    lines.append("")
    lines.append("## 事実")
    lines.append("")
    for i, g in enumerate(_groundings(ob), 1):
        jurisdiction = g.get("jurisdiction", "?")
        if g.get("subdivision"):
            jurisdiction = f"{jurisdiction}-{g['subdivision']}"
        lines.append(f"### {i}. {jurisdiction} — {g.get('source_type', '?')} ({g.get('status', '?')})")
        lines.append("")
        lines.append(f"- authority: {g.get('authority', '—')}")
        lines.append(f"- citation: {g.get('citation', '—')}")
        if g.get("effective"):
            lines.append(f"- effective: {g['effective']}")
        if g.get("applicability"):
            lines.append(f"- applicability: {str(g['applicability']).strip()}")
        for url in g.get("sources", []):
            lines.append(f"- source: {url}")
        lines.append("")
    for heading in ("禁止パターン", "推奨設定", "運用チェック"):
        lines.append(f"## {heading}")
        lines.append("")
        lines.append("<!-- TODO: flesh out with implementation detail grounded in 事実 above. -->")
        lines.append("")
    lines.append("## 制度変更ウォッチ")
    lines.append("")
    lines.append("<!-- 確認TODO: re-review every grounding on its review_by date. -->")
    for i, g in enumerate(_groundings(ob), 1):
        review_by = g.get("review_by", "?")
        lines.append(f"- 確認TODO: {g.get('jurisdiction', '?')} grounding #{i}: review_by {review_by}")
    lines.append("")
    lines.append("<!--")
    lines.append("本セクションは法的助言を構成しません。規制状況は変化します。")
    lines.append("→ https://github.com/ConstitutiveTemplates/law-map (義務グラフの原本)")
    lines.append("-->")
    lines.append("")
    return "\n".join(lines)


def _groundings(ob: Obligation) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for g in ob.data.get("groundings", []):
        if isinstance(g, dict):
            out.append(g)
    return out


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