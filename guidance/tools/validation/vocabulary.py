"""The when / placement / status vocabulary (sections/VOCABULARY.yml)."""

from __future__ import annotations

from pathlib import Path

import yaml

from .const import VOCABULARY

CORE_PACK = "core"


def load_vocabulary(path: Path = VOCABULARY) -> dict:
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        msg = f"{path}: not a mapping"
        raise TypeError(msg)
    return data


def when_groups(vocab: dict) -> list[tuple[str, str, str, dict[str, str]]]:
    """``(kind, name, title, values)`` per group: general, each axis, each extension pack."""
    general = vocab.get("general", {})
    groups = [("general", "general", general.get("title", ""), general.get("values", {}))]
    for kind in ("axes", "extensions"):
        for name, group in (vocab.get(kind) or {}).items():
            groups.append((kind, name, group.get("title", ""), group.get("values", {})))
    return groups


def when_vocab(vocab: dict) -> set[str]:
    return {value for *_, values in when_groups(vocab) for value in values}


def extension_of(vocab: dict) -> dict[str, str]:
    """Condition -> extension pack name, for conditions that live in a pack."""
    return {
        value: name
        for kind, name, _, values in when_groups(vocab)
        if kind == "extensions"
        for value in values
    }


def pack_for(when: list[str], vocab: dict) -> str:
    """The extension pack a section belongs to, or ``core``.

    A section is in a pack when every non-general condition it names comes
    from that one pack (it never applies to a project outside the pack).
    """
    general = set(vocab.get("general", {}).get("values", {}))
    packs = extension_of(vocab)
    names = {packs.get(w, CORE_PACK) for w in when if w not in general}
    return names.pop() if len(names) == 1 else CORE_PACK


def duplicate_conditions(vocab: dict) -> list[str]:
    seen: set[str] = set()
    dupes: list[str] = []
    for *_, values in when_groups(vocab):
        for value in values:
            if value in seen:
                dupes.append(value)
            seen.add(value)
    return dupes
