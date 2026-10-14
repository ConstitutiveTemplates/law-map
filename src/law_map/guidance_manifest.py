"""Regenerate ``guidance/sections/MANIFEST.yml`` from section front matter.

MANIFEST.yml is a generated artifact checked into the repo: the index
consumers (daimonion, architekton-py) read to discover guidance sections
without parsing every file. It embeds the ``when``/``placement``/``status``
vocabulary plus one row per ``guidance/sections/<tier>/<slug>.md`` (id,
file, version, status, placement, when, pack, obligations, triggers).

The implementation is a thin, schema-v2-safe adapter over the merged
``guidance/tools/validation/manifest.py``: it reuses that module's
``build_manifest``/``render_manifest`` so the checked-in file stays
byte-identical to what ``guidance/tools/manifest.py`` writes.
``--check`` (used by ``just check``/CI) exits 1 when the file is stale.
"""

from __future__ import annotations

import sys
from pathlib import Path

__all__ = ["GUIDANCE_DIR_NAME", "MANIFEST_NAME", "default_guidance_root", "manifest_paths", "run_manifest"]


GUIDANCE_DIR_NAME = "guidance"
MANIFEST_NAME = Path("sections") / "MANIFEST.yml"


def default_guidance_root(root: Path) -> Path:
    """``guidance/`` next to the obligations root (``--root``'s parent)."""
    return Path(root).parent / GUIDANCE_DIR_NAME


def manifest_paths(guidance_root: Path) -> tuple[Path, Path, Path]:
    """``(tools_dir, sections_dir, manifest_path)`` for a guidance checkout."""
    base = Path(guidance_root)
    return (base / "tools", base / "sections", base / MANIFEST_NAME)


def run_manifest(guidance_root: Path, *, check: bool) -> int:
    """Regenerate (or ``--check``) the MANIFEST; return the process exit code."""
    tools_dir, sections_dir, manifest_path = manifest_paths(guidance_root)
    vocab_path = sections_dir / "VOCABULARY.yml"
    if not sections_dir.is_dir():
        print(f"error: no guidance sections at {sections_dir}", file=sys.stderr)
        return 1
    sys.path.insert(0, str(tools_dir))
    try:
        from validation.manifest import build_manifest, render_manifest  # type: ignore[import-not-found]
    except ImportError as exc:
        print(f"error: cannot load guidance manifest tooling: {exc}", file=sys.stderr)
        return 1
    finally:
        sys.path.remove(str(tools_dir))
    manifest = build_manifest(sections_dir, vocab_path)
    expected = render_manifest(manifest)
    if check:
        if not manifest_path.is_file() or manifest_path.read_text(encoding="utf-8") != expected:
            print(
                f"error: {manifest_path} is stale; run `law-map manifest`",
                file=sys.stderr,
            )
            return 1
        print(f"ok: {manifest_path} in sync ({len(manifest['sections'])} sections)")
        return 0
    if manifest_path.is_file() and manifest_path.read_text(encoding="utf-8") == expected:
        print(f"unchanged: {manifest_path}")
        return 0
    manifest_path.write_text(expected, encoding="utf-8")
    print(f"wrote {manifest_path} ({len(manifest['sections'])} sections)")
    return 0
