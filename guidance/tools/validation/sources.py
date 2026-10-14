"""Declared-source URL collection: section files and YAML data files."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from urllib.parse import urlparse

import yaml

from .const import (
    SECTION_GLOB,
    SECTIONS,
    URL_RE,
)
from .frontmatter import split_front_matter

# Generated / vocabulary files carry no `sources:` of their own.
_NON_DATA_YAML = frozenset({"MANIFEST.yml", "VOCABULARY.yml"})


def strip_url_punct(url: str) -> str:
    """Drop trailing prose punctuation the URL regex may have swallowed."""
    return url.rstrip(".,;:!?")


def _split_front_matter_sources(text: str) -> tuple[list[str], str]:
    """Split section text into (front matter ``sources`` list, body)."""
    try:
        front, body = split_front_matter(text)
    except yaml.YAMLError:
        return [], text
    sources = front.get("sources") if front else None
    head = [s for s in sources if isinstance(s, str)] if isinstance(sources, list) else []
    return head, body


def extract_section_urls(text: str) -> list[str]:
    """URLs declared by one section file: front matter sources + body links."""
    head, body = _split_front_matter_sources(text)
    head_urls = [u for s in head for u in URL_RE.findall(s)]
    return [strip_url_punct(u) for u in head_urls + URL_RE.findall(body)]


def _collect_yaml_source_urls(node: object, found: list[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "sources" and isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        url = strip_url_punct(item.strip())
                        if url.startswith(("http://", "https://")):
                            found.append(url)
            else:
                _collect_yaml_source_urls(value, found)
    elif isinstance(node, list):
        for item in node:
            _collect_yaml_source_urls(item, found)


def extract_yaml_sources(doc: object) -> list[str]:
    """URL strings under any `sources:` list in a YAML doc (e.g. lang/*.yml)."""
    found: list[str] = []
    _collect_yaml_source_urls(doc, found)
    return found


def _add_source_urls(collected: dict[str, set[str]], origin: str, urls: Iterable[str]) -> None:
    for url in urls:
        parsed = urlparse(url)
        if parsed.scheme in ("http", "https") and parsed.netloc:
            collected.setdefault(origin, set()).add(url)


def _section_file_source_urls(sections_dir: Path, collected: dict[str, set[str]]) -> None:
    for path in sorted(sections_dir.glob(SECTION_GLOB)):
        _add_source_urls(collected,
                         path.relative_to(sections_dir).as_posix(),
                         extract_section_urls(path.read_text(encoding="utf-8")))


def _yaml_data_source_urls(sections_dir: Path, collected: dict[str, set[str]]) -> None:
    for pattern in ("*.yml", "*.yaml"):
        for path in sorted(sections_dir.rglob(pattern)):
            if path.name in _NON_DATA_YAML:
                continue
            with path.open(encoding="utf-8") as fh:
                doc = yaml.safe_load(fh)
            _add_source_urls(collected,
                             path.relative_to(sections_dir).as_posix(),
                             extract_yaml_sources(doc))


def collect_source_urls(sections_dir: Path = SECTIONS) -> dict[str, list[str]]:
    """Map relative file path -> sorted unique declared source URLs.

    Covers every ``sections/*/*.md`` (front matter ``sources:`` + body links)
    and sibling YAML data files (any ``sources:`` list, e.g.
    ``lang/copyright-terms.yml``). Reads files only; never touches
    the network.
    """
    collected: dict[str, set[str]] = {}
    _section_file_source_urls(sections_dir, collected)
    _yaml_data_source_urls(sections_dir, collected)
    return {origin: sorted(urls) for origin, urls in sorted(collected.items())}
