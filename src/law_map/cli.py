"""Command-line interface for the law-map obligation corpus."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

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
        help="obligations corpus directory (default: repo obligations/)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate", help="validate the corpus against the schema rules")
    p_validate.add_argument("--warnings", action="store_true", help="also print non-fatal warnings")

    sub.add_parser("list", help="list obligation ids")

    p_show = sub.add_parser("show", help="show one obligation")
    p_show.add_argument("id", help="obligation id to show")

    p_check = sub.add_parser("check", help="report groundings due for review")
    p_check.add_argument("--days", type=int, default=30, help="review horizon in days (default 30)")
    p_check.add_argument(
        "--sources",
        action="store_true",
        help="HEAD-check grounding source URLs (network access)",
    )

    p_export = sub.add_parser("export", help="render obligations as .md.jinja codex sections")
    p_export.add_argument("--out", type=Path, default=Path("out"), help="output directory")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    from . import check as check_mod
    from . import export as export_mod
    from . import model as model_mod

    corpus = model_mod.load_corpus(args.root)
    checks_root = args.root.parent / "checks"
    model_mod.check_cross_references(corpus, checks_root=checks_root if checks_root.is_dir() else None)

    if args.command == "validate":
        return _cmd_validate(args, corpus)
    if args.command == "list":
        return _cmd_list(corpus)
    if args.command == "show":
        return _cmd_show(args, corpus)
    if args.command == "check":
        return _cmd_check(args, corpus, check_mod)
    if args.command == "export":
        return _cmd_export(args, corpus, export_mod)
    raise AssertionError(f"unhandled command {args.command!r}")


def _cmd_validate(args: argparse.Namespace, corpus: Any) -> int:
    for issue in corpus.errors:
        print(f"error: {issue}", file=sys.stderr)
    if args.warnings:
        for issue in corpus.warnings:
            print(f"warning: {issue}", file=sys.stderr)
    n = len(corpus.obligations)
    if corpus.ok():
        print(f"ok: {n} obligation(s), no errors")
        return 0
    print(f"failed: {n} obligation(s), {len(corpus.errors)} error(s)", file=sys.stderr)
    return 1


def _cmd_list(corpus: Any) -> int:
    for ob in sorted(corpus.obligations, key=lambda o: o.id):
        print(ob.id)
    return 0


def _cmd_show(args: argparse.Namespace, corpus: Any) -> int:
    norm = args.id.replace("/", ".")
    if norm.startswith("obligation."):
        norm = norm[len("obligation."):]
    full = "obligation." + norm
    match = [ob for ob in corpus.obligations if ob.id == args.id or ob.id == full or ob.id.endswith("." + norm)]
    if not match:
        print(f"no obligation matches '{args.id}'", file=sys.stderr)
        return 1
    import yaml

    data = {k: v for k, v in match[0].data.items() if not k.startswith("_")}
    print(yaml.safe_dump(data, sort_keys=False, allow_unicode=True).rstrip())
    return 0


def _cmd_check(args: argparse.Namespace, corpus: Any, check_mod: Any) -> int:
    report = check_mod.run_check(corpus, today=check_mod.today(), days=args.days, sources=args.sources)
    for e in report.expiry:
        state = "EXPIRED" if e.expired else f"due by {e.review_by}"
        print(f"[{state}] {e.obligation_id} ({e.jurisdiction}): {e.citation}")
    for p in report.probes:
        if p.problem is not None:
            print(f"[source {p.problem}] {p.url}")
    if report.probes:
        flagged = sum(1 for p in report.probes if p.problem is not None)
        print(f"source probes: {len(report.probes)} total, {flagged} flagged")
    if report.expired:
        print(f"{len(report.expired)} grounding(s) expired — exit 1", file=sys.stderr)
        return 1
    print(f"review check: {len(report.expiry)} due within {args.days} day(s), 0 expired")
    return 0


def _cmd_export(args: argparse.Namespace, corpus: Any, export_mod: Any) -> int:
    written = export_mod.export_obligations(corpus.obligations, args.out)
    for path in written:
        print(f"wrote {path}")
    if not written:
        print("nothing to export: corpus is empty", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())