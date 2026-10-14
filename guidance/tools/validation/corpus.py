"""Corpus validators: front matter, bodies, review dates, generated MANIFEST."""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

import yaml

from .const import (
    BANNED_PHRASES,
    EN_KEYS,
    FRONT_MATTER_KEYS,
    JINJA_RE,
    LICENSE_FILE,
    LICENSE_NOTE,
    OBLIGATION_ID_RE,
    REPO,
    REQUIRED_HEADINGS,
    REVIEW_BY_RE,
    REVIEW_HORIZON,
    SECTION_GLOB,
    SECTION_LICENSE,
    SECTION_LICENSE_HEAD,
    SECTION_SUFFIX,
    SECTIONS,
    TRIGGER_KEYS,
    VERSION_RE,
)
from .frontmatter import split_front_matter
from .manifest import expected_outputs, stale_outputs
from .report import error, warn
from .upstream import obligation_sections
from .vocabulary import duplicate_conditions, load_vocabulary, when_vocab


def section_files() -> list[Path]:
    return sorted(SECTIONS.glob(SECTION_GLOB))


def expected_id(path: Path) -> str:
    """region/eu-cra.md -> region-eu-cra (tier-slug naming rule)."""
    return f"{path.parent.name}-{path.name.removesuffix(SECTION_SUFFIX)}"


def _is_str_list(value: object, *, allow_empty: bool = False) -> bool:
    return (
        isinstance(value, list)
        and (allow_empty or bool(value))
        and all(isinstance(v, str) and v.strip() for v in value)
    )


def _check_regex(path: Path, key: str, value: object) -> None:
    if not isinstance(value, str) or not value:
        error(f"{path}: triggers.{key} must be a non-empty regex string")
        return
    try:
        re.compile(value)
    except re.error as exc:
        error(f"{path}: triggers.{key} does not compile: {exc}")


def _check_triggers(path: Path, triggers: object) -> None:
    if not isinstance(triggers, dict):
        error(f"{path}: triggers must be a mapping with keywords/pattern")
        return
    for key in sorted(set(triggers) - set(TRIGGER_KEYS)):
        error(f"{path}: unknown triggers key {key!r} (allowed: {', '.join(TRIGGER_KEYS)})")
    if not _is_str_list(triggers.get("keywords")):
        error(f"{path}: triggers.keywords must be a non-empty string list")
    _check_regex(path, "pattern", triggers.get("pattern"))
    if "config" in triggers:
        _check_regex(path, "config", triggers["config"])


def _check_en(path: Path, en: object) -> None:
    if not isinstance(en, dict):
        error(f"{path}: en must be a mapping with title/summary/prohibited")
        return
    for key in sorted(set(en) - set(EN_KEYS)):
        error(f"{path}: unknown en key {key!r} (allowed: {', '.join(EN_KEYS)})")
    if not isinstance(en.get("title"), str) or not en["title"].strip():
        error(f"{path}: en.title must be a non-empty string")
    for key in ("summary", "prohibited"):
        if not _is_str_list(en.get(key)):
            error(f"{path}: en.{key} must be a non-empty string list")


def _check_when(path: Path, when: object, vocab: set[str]) -> None:
    items = when if isinstance(when, list) else [when]
    if not items or not all(isinstance(w, str) for w in items):
        error(f"{path}: when must be a condition or a non-empty list of conditions")
        return
    bad = [w for w in items if w not in vocab]
    if bad:
        error(f"{path}: when {bad!r} not in VOCABULARY.yml {sorted(vocab)}")


def check_front_matter(path: Path, front: dict, vocab: dict) -> None:
    for key in FRONT_MATTER_KEYS:
        if key not in front:
            error(f"{path}: front matter missing {key!r}")
    for key in sorted(set(front) - set(FRONT_MATTER_KEYS)):
        error(f"{path}: unknown front matter key {key!r}")
    sid = front.get("id")
    exp = expected_id(path)
    if sid != exp:
        error(f"{path}: id {sid!r} != path-derived id {exp!r}")
    version = front.get("version")
    if not isinstance(version, str) or not VERSION_RE.fullmatch(version):
        error(f"{path}: version must be a quoted 'YYYY-MM-DD.rev' string (got {version!r})")
    if front.get("status") not in vocab.get("status", {}):
        error(f"{path}: status {front.get('status')!r} not in {sorted(vocab.get('status', {}))}")
    if front.get("placement") not in vocab.get("placement", {}):
        error(f"{path}: placement {front.get('placement')!r} not in {sorted(vocab.get('placement', {}))}")
    if "when" in front:
        _check_when(path, front["when"], when_vocab(vocab))
    obligations = front.get("obligations", [])
    if not _is_str_list(obligations, allow_empty=True):
        error(f"{path}: obligations must be a list of law-map obligation ids")
    else:
        for ob in obligations:
            if not OBLIGATION_ID_RE.fullmatch(ob):
                error(f"{path}: obligation id {ob!r} is not 'obligation.<category>.<slug>'")
    if "triggers" in front:
        _check_triggers(path, front["triggers"])
    sources = front.get("sources", [])
    if not _is_str_list(sources) or not all(s.startswith(("http://", "https://")) for s in sources):
        error(f"{path}: sources must be a non-empty list of http(s) URLs")
    if front.get("license") != SECTION_LICENSE:
        error(f"{path}: license must be {SECTION_LICENSE!r} (section prose is CC BY 4.0)")
    if "en" in front:
        _check_en(path, front["en"])


def check_headings(path: Path, body: str) -> None:
    if not body.lstrip("\n").startswith("# "):
        error(f"{path}: body must open with a '# <title>' line")
    positions: dict[str, int] = {}
    for heading in REQUIRED_HEADINGS:
        idx = body.find(heading)
        if idx < 0:
            error(f"{path}: missing required heading {heading!r}")
        else:
            positions[heading] = idx
    if len(positions) == len(REQUIRED_HEADINGS):
        order = [positions[h] for h in REQUIRED_HEADINGS]
        if order != sorted(order):
            error(f"{path}: required headings out of order {REQUIRED_HEADINGS}")


def _report_review_date(path: Path, due: dt.date, today: dt.date, *, drift_mode: bool) -> None:
    if due < today:
        msg = f"{path}: review_by {due} expired (today {today})"
        if drift_mode:
            print(f"[drift] EXPIRED {msg}")
        else:
            error(msg)
    elif due <= today + REVIEW_HORIZON:
        msg = f"{path}: review_by {due} due within 30 days (today {today})"
        if drift_mode:
            print(f"[drift] due {msg}")
        else:
            warn(msg)


def check_review_by(
    path: Path,
    body: str,
    drift_mode: bool = False,
    *,
    required: bool = True,
) -> list[tuple[str, dt.date]]:
    """Check ``(review_by: YYYY-MM-DD)`` dates in a body.

    ``required`` is False for sections that reference law-map obligations:
    law-map owns their freshness, so a missing date is not an error. Dates
    that are present are still checked -- an expired one is a stale claim.
    """
    found = [(m.group(1), dt.date.fromisoformat(m.group(1))) for m in REVIEW_BY_RE.finditer(body)]
    if not found:
        if required and not drift_mode:
            error(f"{path}: no (review_by: YYYY-MM-DD) date in 制度変更ウォッチ "
                  "and no law-map obligations to own its freshness")
        return found
    today = dt.datetime.now(dt.UTC).date()
    for _, due in found:
        _report_review_date(path, due, today, drift_mode=drift_mode)
    return found


def check_flag_agnostic(path: Path, body: str) -> None:
    for match in JINJA_RE.finditer(body):
        snippet = body[max(0, match.start() - 25): match.start() + 10].replace("\n", " ")
        error(f"{path}: template expression {match.group(0)!r} in body (near {snippet!r})")


def check_banned_phrases(path: Path, text: str, where: str) -> None:
    for pattern, reason in BANNED_PHRASES:
        for match in pattern.finditer(text):
            error(f"{path}: {where} contains {match.group(0)!r} ({reason})")


def check_license_note(path: Path, body: str, sid: object) -> None:
    note = LICENSE_NOTE.format(id=sid)
    if body.rstrip("\n").splitlines()[-1:] != [note]:
        error(f"{path}: body must end with the CC BY 4.0 attribution note: {note}")


def check_license_file(path: Path = LICENSE_FILE) -> None:
    if not path.is_file() or not path.read_text(encoding="utf-8").startswith(SECTION_LICENSE_HEAD):
        error(f"{path}: missing CC BY 4.0 legal code for the section prose")


def _en_text(front: dict) -> str:
    en = front.get("en")
    if not isinstance(en, dict):
        return ""
    parts = [str(en.get("title", ""))]
    for key in ("summary", "prohibited"):
        value = en.get(key)
        if isinstance(value, list):
            parts += [str(v) for v in value]
    return "\n".join(parts)


def _validate_section_file(path: Path, vocab: dict, seen_ids: set[str], *, drift_mode: bool) -> None:
    text = path.read_text(encoding="utf-8")
    try:
        front, body = split_front_matter(text)
    except yaml.YAMLError as exc:
        error(f"{path}: front matter is not valid YAML: {exc}")
        return
    if front is None:
        error(f"{path}: missing '---' YAML front matter")
        return
    check_front_matter(path, front, vocab)
    sid = front.get("id")
    if isinstance(sid, str):
        if sid in seen_ids:
            error(f"{path}: duplicate section id {sid!r}")
        seen_ids.add(sid)
    check_flag_agnostic(path, body)
    check_banned_phrases(path, body, "body")
    check_banned_phrases(path, _en_text(front), "en block")
    check_headings(path, body)
    check_license_note(path, body, sid)
    check_review_by(path, body, drift_mode=drift_mode, required=not front.get("obligations"))


def validate_section_files(files: list[Path], vocab: dict, *, drift_mode: bool) -> None:
    seen_ids: set[str] = set()
    for path in files:
        _validate_section_file(path, vocab, seen_ids, drift_mode=drift_mode)


def check_law_map_links(files: list[Path], links: dict[str, set[str]] | None) -> None:
    """Warn when a section's ``obligations`` and law-map's ``related_sections`` disagree."""
    if links is None:
        return
    for path in files:
        try:
            front, _ = split_front_matter(path.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        if not front or not isinstance(front.get("obligations"), list):
            continue
        ours = set(front["obligations"])
        theirs = links.get(str(front.get("id")), set())
        if ours != theirs:
            warn(f"{path}: obligations {sorted(ours)} != law-map related_sections {sorted(theirs)}")


def check_generated_in_sync() -> None:
    try:
        outputs = expected_outputs()
    except (OSError, yaml.YAMLError, TypeError) as exc:
        error(f"cannot regenerate MANIFEST.yml: {exc}")
        return
    for path in stale_outputs(outputs):
        error(f"{path.relative_to(REPO)}: out of sync with section front matter (run `just manifest`)")


def validate_corpus(*, drift_mode: bool = False) -> list[Path]:
    """Validate every section file and the generated MANIFEST; return the files."""
    vocab = load_vocabulary()
    for dupe in duplicate_conditions(vocab):
        error(f"VOCABULARY.yml: condition {dupe!r} appears in more than one group")
    check_license_file()
    files = section_files()
    validate_section_files(files, vocab, drift_mode=drift_mode)
    check_law_map_links(files, obligation_sections())
    check_generated_in_sync()
    return files
