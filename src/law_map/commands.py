"""Handlers for the ``law-map`` subcommands.

Argument parsing and dispatch live in :mod:`law_map.cli`; this module
implements one ``cmd_*`` function per subcommand plus the small output
helpers they share.
"""

from __future__ import annotations

import argparse
import sys

from . import check, stats, watch
from .export import export_obligations
from .model import Corpus

__all__ = ["cmd_check", "cmd_export", "cmd_list", "cmd_show", "cmd_stats", "cmd_validate", "cmd_watch"]


def cmd_validate(args: argparse.Namespace, corpus: Corpus) -> int:
    if _report_empty_root(args, corpus):
        return 1
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
    if _report_empty_root(args, corpus):
        return 1
    if getattr(args, "kanon", None) is not None:
        _print_issues("error", corpus.errors)
        if corpus.errors:
            print(
                f"check failed: {len(corpus.errors)} corpus error(s) with --kanon — exit 1",
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


def cmd_stats(args: argparse.Namespace, corpus: Corpus) -> int:
    if _report_empty_root(args, corpus):
        return 1
    if not args.markdown:
        if args.check or args.write:
            print("error: --check/--write need --markdown", file=sys.stderr)
            return 2
        print(stats.render_text(corpus), end="")
        return 0
    rendered = stats.render_markdown(corpus)
    try:
        if args.check is not None:
            if stats.check_block(args.check, rendered):
                print(f"ok: {args.check} stats block matches the corpus")
                return 0
            print(
                f"error: {args.check} stats block is stale; run "
                f"`law-map stats --markdown --write {args.check}`",
                file=sys.stderr,
            )
            return 1
        if args.write is not None:
            changed = stats.replace_block(args.write, rendered)
            print(f"{'updated' if changed else 'unchanged'}: {args.write}")
            return 0
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(rendered, end="")
    return 0


def cmd_watch(args: argparse.Namespace, corpus: Corpus) -> int:
    if _report_empty_root(args, corpus):
        return 1
    probes = watch.watch_laws(corpus)
    for probe in probes:
        line = watch.format_watch_line(probe)
        if line is not None:
            print(line)
    print(watch.format_watch_summary(probes))
    return 1 if any(p.problem == "changed" for p in probes) else 0


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

def _report_empty_root(args: argparse.Namespace, corpus: Corpus) -> bool:
    """Print an error and return True when ``--root`` is missing or holds no obligations.

    An installed wheel's default root points at a path that does not exist;
    reporting "ok: 0 obligation(s)" there would pass CI on an empty corpus.
    """
    root = args.root
    if not root.is_dir():
        problem = f"obligations root {root} does not exist"
    elif not corpus.obligations and corpus.excluded:
        print(f"error: no obligations in pack(s) {', '.join(args.packs)} under {root}", file=sys.stderr)
        return True
    elif not corpus.obligations and not corpus.errors:
        problem = f"no obligations found under {root}"
    else:
        return False
    print(f"error: {problem}; pass --root <law-map checkout>/obligations", file=sys.stderr)
    return True


def _print_issues(prefix: str, issues: list[str]) -> None:
    for issue in issues:
        print(f"{prefix}: {issue}", file=sys.stderr)
