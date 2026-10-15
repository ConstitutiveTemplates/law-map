"""Command-line interface for the law-map obligation corpus."""

from __future__ import annotations

import argparse
from pathlib import Path

from . import check as check_mod
from . import checkspecs, commands
from .loader import load_corpus
from .model import PACKS
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
    parser.add_argument(
        "--pack",
        dest="packs",
        action="append",
        choices=PACKS,
        default=None,
        help=(
            "load only this pack (repeatable; default: all). core = statutes, "
            "regulations, case law; guidance = official guidance and standards; "
            "community = private rules and incident lessons. Every file is still "
            "validated, and requires/conflicts resolve across packs"
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate", help="validate the corpus against the schema rules")
    p_validate.add_argument("--warnings", action="store_true", help="also print non-fatal warnings")
    p_validate.add_argument(
        "--kanon",
        "--codex",
        type=Path,
        default=None,
        help=(
            "path to a guidance checkout (default: this repo's guidance/); every "
            "related_sections id must resolve to guidance/sections/<tier>/<slug>.md "
            "(errors on unresolved ids); guidance sections no obligation "
            "references become warnings"
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
        "--kanon",
        "--codex",
        type=Path,
        default=None,
        help=(
            "path to a guidance checkout (default: this repo's guidance/); every "
            "related_sections id must resolve to guidance/sections/<tier>/<slug>.md "
            "(errors on unresolved ids)"
        ),
    )

    p_stats = sub.add_parser("stats", help="corpus scope: jurisdictions, categories, binding levels")
    p_stats.add_argument("--markdown", action="store_true", help="render the README scope tables")
    stats_target = p_stats.add_mutually_exclusive_group()
    stats_target.add_argument(
        "--check",
        type=Path,
        metavar="FILE",
        default=None,
        help="exit 1 when the stats block in FILE (e.g. README.md) differs from the corpus",
    )
    stats_target.add_argument(
        "--write", type=Path, metavar="FILE", default=None, help="rewrite the stats block in FILE"
    )

    sub.add_parser(
        "watch",
        help=(
            "law-watch: ask EUR-Lex, e-Gov, legislation.gov.uk and the RFC Editor whether cited "
            "instruments were amended after each grounding's reviewed_on/effective (network)"
        ),
    )

    p_export = sub.add_parser("export", help="render obligations as guidance-format .md section drafts")
    p_export.add_argument("--out", type=Path, default=Path("out"), help="output directory")

    p_migrate = sub.add_parser(
        "migrate", help="convert schema-v1 obligations to v2 (mechanical part; expert fields stay for review)"
    )
    p_migrate.add_argument(
        "--in",
        dest="migrate_in",
        type=Path,
        required=True,
        help="v1 obligations directory to read",
    )
    p_migrate.add_argument("--out", type=Path, required=True, help="directory to write migrated v2 files into")

    p_hashes = sub.add_parser(
        "record-hashes",
        help="fetch open_law texts and record verified_text_sha256 per grounding (network)",
    )
    p_hashes.add_argument(
        "--write",
        action="store_true",
        help="patch the obligation files (default is a dry run printing the hashes)",
    )

    p_manifest = sub.add_parser("manifest", help="regenerate guidance/sections/MANIFEST.yml from section front matter")
    p_manifest.add_argument(
        "--check",
        action="store_true",
        help="do not write; exit 1 when the checked-in MANIFEST is stale",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "migrate":
        # v1 input cannot pass v2 validation, so migrate runs on raw files.
        return commands.cmd_migrate(args)
    corpus = load_corpus(args.root, today=check_mod.today(), packs=args.packs)

    checks_root = args.root.parent / "checks"
    guidance_default = args.root.parent / "guidance"
    codex_root = getattr(args, "kanon", None)
    if codex_root is None and (guidance_default / "sections").is_dir():
        codex_root = guidance_default  # merged rulebook: validate against guidance/ by default
    if codex_root is not None and not (codex_root / "sections").is_dir():
        corpus.errors.append(f"--kanon {codex_root}: not a guidance checkout (no sections/ directory)")
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
    if args.command == "stats":
        return commands.cmd_stats(args, corpus)
    if args.command == "watch":
        return commands.cmd_watch(args, corpus)
    if args.command == "export":
        return commands.cmd_export(args, corpus)
    if args.command == "record-hashes":
        return commands.cmd_record_hashes(args, corpus)
    if args.command == "manifest":
        return commands.cmd_manifest(args)
    raise AssertionError(f"unhandled command {args.command!r}")


if __name__ == "__main__":
    raise SystemExit(main())
