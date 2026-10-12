"""Handlers for the ``law-map`` subcommands.

Argument parsing and dispatch live in :mod:`law_map.cli`; this module
implements one ``cmd_*`` function per subcommand plus the small output
helpers they share.
"""

from __future__ import annotations

import argparse
import sys

from . import check
from .export import export_obligations
from .model import Corpus

__all__ = ["cmd_check", "cmd_export", "cmd_list", "cmd_show", "cmd_validate"]


def cmd_validate(args: argparse.Namespace, corpus: Corpus) -> int:
    _print_issues("error", corpus.errors)
    if args.warnings:
        _print_issues("warning", corpus.warnings)
    n = len(corpus.obligations)
    if corpus.ok():
        print(f"ok: {n} obligation(s), no errors")
        return 0
    print(f"failed: {n} obligation(s), {len(corpus.errors)} error(s)", file=sys.stderr)
    return 1


def cmd_list(corpus: Corpus) -> int:
    for ob in sorted(corpus.obligations, key=lambda o: o.id):
        print(ob.id)
    return 0


def cmd_show(args: argparse.Namespace, corpus: Corpus) -> int:
    norm = args.id.replace("/", ".")
    if norm.startswith("obligation."):
        norm = norm[len("obligation.") :]
    full = "obligation." + norm
    match = [ob for ob in corpus.obligations if ob.id == args.id or ob.id == full or ob.id.endswith("." + norm)]
    if not match:
        print(f"no obligation matches '{args.id}'", file=sys.stderr)
        return 1
    import yaml

    data = {k: v for k, v in match[0].data.items() if not k.startswith("_")}
    print(yaml.safe_dump(data, sort_keys=False, allow_unicode=True).rstrip())
    return 0


def cmd_check(args: argparse.Namespace, corpus: Corpus) -> int:
    if getattr(args, "codex", None) is not None:
        _print_issues("error", corpus.errors)
        if corpus.errors:
            print(
                f"check failed: {len(corpus.errors)} corpus error(s) with --codex — exit 1",
                file=sys.stderr,
            )
            return 1
    report = check.run_check(corpus, today=check.today(), days=args.days, sources=args.sources)
    print_check_report(report)
    if report.expired:
        print(f"{len(report.expired)} grounding(s) expired — exit 1", file=sys.stderr)
        return 1
    print(f"review check: {len(report.expiry)} due within {args.days} day(s), 0 expired")
    return 0


def cmd_export(args: argparse.Namespace, corpus: Corpus) -> int:
    written = export_obligations(corpus.obligations, args.out, today=check.today())
    for path in written:
        print(f"wrote {path}")
    if not written:
        print("nothing to export: corpus is empty", file=sys.stderr)
        return 1
    return 0


def print_check_report(report: check.CheckReport) -> None:
    for e in report.expiry:
        print(check.format_expiry_line(e))
    for probe in report.probes:
        line = check.format_source_line(probe)
        if line is not None:
            print(line)
    if report.probes:
        print(check.format_source_summary(report.probes))
    for open_law_probe in report.open_law:
        line = check.format_open_law_line(open_law_probe)
        if line is not None:
            print(line)
    if report.open_law:
        print(check.format_open_law_summary(report.open_law))

def _print_issues(prefix: str, issues: list[str]) -> None:
    for issue in issues:
        print(f"{prefix}: {issue}", file=sys.stderr)
