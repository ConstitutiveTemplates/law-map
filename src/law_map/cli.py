"""Command-line interface for the law-map obligation corpus."""

from __future__ import annotations

import argparse
from pathlib import Path

from . import check as check_mod
from . import checkspecs, commands
from .loader import load_corpus
from .refs import check_cross_references

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _default_root() -> Path:
    """Repo-relative corpus location; overridable with --root for tests."""
    return REPO_ROOT / "obligations"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="law-map",
        description="Organize law as technical obligations mapped to jurisdiction groundings.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=_default_root(),
        help=(
            "obligations corpus directory (default: obligations/ of the source checkout; "
            "pass it explicitly when law-map is installed from a wheel)"
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate", help="validate the corpus against the schema rules")
    p_validate.add_argument("--warnings", action="store_true", help="also print non-fatal warnings")
    p_validate.add_argument(
        "--kanon", "--codex",
        type=Path,
        default=None,
        help=(
            "path to a kanon checkout; every related_sections id must "
            "resolve to sections/<tier>/<slug>.md.jinja (errors on unresolved ids); "
            "kanon sections no obligation references become warnings"
        ),
    )

    sub.add_parser("list", help="list obligation ids")

    p_show = sub.add_parser("show", help="show one obligation")
    p_show.add_argument("id", help="obligation id to show")

    p_check = sub.add_parser("check", help="report groundings due for review")
    p_check.add_argument("--days", type=int, default=30, help="review horizon in days (default 30)")
    p_check.add_argument(
        "--sources",
        action="store_true",
        help="HEAD-check grounding source URLs and resolve open_law refs via open-law (network access)",
    )
    p_check.add_argument(
        "--kanon", "--codex",
        type=Path,
        default=None,
        help=(
            "path to a kanon checkout; every related_sections id must "
            "resolve to sections/<tier>/<slug>.md.jinja (errors on unresolved ids)"
        ),
    )

    p_export = sub.add_parser("export", help="render obligations as .md.jinja kanon sections")
    p_export.add_argument("--out", type=Path, default=Path("out"), help="output directory")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    corpus = load_corpus(args.root, today=check_mod.today())

    checks_root = args.root.parent / "checks"
    codex_root = getattr(args, "kanon", None)
    if codex_root is not None and not (codex_root / "sections").is_dir():
        corpus.errors.append(f"--kanon {codex_root}: not a kanon checkout (no sections/ directory)")
        codex_root = None  # avoid redundant per-id errors from a broken path
    check_cross_references(
        corpus,
        checks_root=checks_root if checks_root.is_dir() else None,
        codex_root=codex_root,
    )
    checkspecs.validate_check_specs(checks_root, corpus)

    if args.command == "validate":
        return commands.cmd_validate(args, corpus)
    if args.command == "list":
        return commands.cmd_list(corpus)
    if args.command == "show":
        return commands.cmd_show(args, corpus)
    if args.command == "check":
        return commands.cmd_check(args, corpus)
    if args.command == "export":
        return commands.cmd_export(args, corpus)
    raise AssertionError(f"unhandled command {args.command!r}")


if __name__ == "__main__":
    raise SystemExit(main())
