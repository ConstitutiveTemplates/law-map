"""Schema v1 -> v2 migration for obligation documents.

Mechanical changes only: ``version`` 1 -> 2, a ``source_kind`` per
grounding inferred from its source hosts (reported for human review —
the migrator cannot tell a regulator's guidance page from the gazette
by URL alone), and the European Accessibility Act's move from the
``privacy`` domain to the new ``accessibility`` category.

What migration does *not* do is the expert work: confirming each
inferred ``source_kind``, recording ``negative_history``,
``scope``/``exceptions``/``strength``/``confidence``, peer review (``reviewed_by`` +
``reviewed_on``), and ``verified_text_sha256`` (see
``law-map record-hashes``). Files are rewritten with PyYAML, so comments
do not survive — review the diff before committing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from .model import SCHEMA_VERSION, UNOFFICIAL_HOSTS

__all__ = [
    "MIGRATED_IDENTITY",
    "infer_source_kind",
    "migrate_document",
    "migrate_tree",
]

# (old obligation id, new obligation id).
MIGRATED_IDENTITY = (
    (
        "obligation.privacy.european-accessibility-act",
        "obligation.accessibility.european-accessibility-act",
    ),
)

# Hosts whose pages are the instrument itself (the gazette, the ELI URL,
# the publisher's own rules page).
PRIMARY_HOSTS = (
    "eur-lex.europa.eu",
    "laws.e-gov.go.jp",
    "www.legislation.gov.uk",
    "legislation.gov.uk",
    "statutes.capitol.texas.gov",
    "www.ilga.gov",
    "ilga.gov",
    "csrc.nist.gov",
    "www.pcisecuritystandards.org",
    "pcisecuritystandards.org",
    "www.etsi.org",
    "etsi.org",
    "www.rfc-editor.org",
    "rfc-editor.org",
    "info.atcoder.jp",
)


def _unofficial_host(host: str) -> bool:
    if host in UNOFFICIAL_HOSTS:
        return True
    if host.endswith(".archives.gov") and host != "www.archives.gov":
        return True
    # Conference slide decks, community standards, third-party write-ups.
    return host in (
        "2017.apricot.net",
        "genai.owasp.org",
        "www.ifross.org",
        "www.cric.or.jp",
    )


def infer_source_kind(sources: object) -> str:
    """Best-effort ``source_kind`` from source hosts; always human-reviewable."""
    if not isinstance(sources, list) or not sources:
        return "official-secondary"
    hosts = [(urlparse(u).hostname or "").lower() for u in sources if isinstance(u, str)]
    if any(_unofficial_host(h) for h in hosts):
        return "unofficial"
    if any(h in PRIMARY_HOSTS for h in hosts):
        return "primary"
    return "official-secondary"


def migrate_document(data: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Migrate one parsed v1 document to v2; notes describe every inference.

    Raises ValueError when the document is not a v1 obligation.
    """
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError(f"not a schema-v1 obligation document (version={data.get('version')!r})")
    notes: list[str] = []
    data = {**data, "version": SCHEMA_VERSION}
    for old_id, new_id in MIGRATED_IDENTITY:
        if data.get("id") == old_id:
            data["id"] = new_id
            data["category"] = "accessibility"
            notes.append(f"moved {old_id} -> {new_id} (category accessibility)")
    groundings = data.get("groundings")
    if isinstance(groundings, list):
        for i, g in enumerate(groundings):
            if not isinstance(g, dict):
                continue
            if "source_kind" not in g:
                kind = infer_source_kind(g.get("sources"))
                g["source_kind"] = kind
                notes.append(f"groundings[{i}] ({g.get('jurisdiction')}) source_kind inferred as {kind!r}")
    return data, notes


def migrate_tree(root: Path, out: Path) -> dict[str, list[str]]:
    """Migrate every ``*.yml`` obligation under *root* into *out*; returns notes per file.

    Underscore-prefixed files (e.g. ``_example.yml``) are copied unchanged.
    Domain directories are derived from the migrated obligation id, so the
    accessibility move lands in the right directory. Raises ValueError on
    the first non-v1 document.
    """
    root, out = Path(root), Path(out)
    report: dict[str, list[str]] = {}
    for path in sorted(root.rglob("*.yml")):
        rel = path.relative_to(root)
        if path.name.startswith("_"):
            target = out / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())
            report[str(rel)] = ["copied unchanged (corpus-excluded)"]
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"{path}: document must be a mapping")
        migrated, notes = migrate_document(data)
        domain = str(migrated.get("id", "")).split(".")
        target = out / (domain[1] if len(domain) > 1 else rel.parent.name) / path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(yaml.safe_dump(migrated, sort_keys=False, allow_unicode=True), encoding="utf-8")
        report[str(rel)] = notes or ["migrated without inferences"]
    return report
