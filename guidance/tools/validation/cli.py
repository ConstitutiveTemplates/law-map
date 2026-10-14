"""Argparse entry point: check (default), --drift, --sources."""

from __future__ import annotations

import argparse
import sys

from .corpus import validate_corpus
from .liveness import drift_report, run_sources_check
from .report import errors, warnings


def print_validation_report(file_count: int) -> int:
    for msg in errors:
        print(f"error: {msg}", file=sys.stderr)
    for msg in warnings:
        print(f"warning: {msg}")
    if errors:
        print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"ok: {file_count} sections validate ({len(warnings)} warning(s))")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--drift", action="store_true",
                        help="print due/expired review_by + probe declared source URLs; exit 0 always")
    parser.add_argument("--sources", action="store_true",
                        help="HEAD/GET-check declared sources: URLs (network access); "
                        "exit 1 when any URL is flagged (with --drift: single probe run, exit reflects sources)")
    parser.add_argument("--strict-obligations", action="store_true",
                        help="error (not warn) on section obligations: refs with no "
                        "obligations/<domain>/<slug>.yml in law-map")
    args = parser.parse_args(argv)

    files = validate_corpus(drift_mode=args.drift, strict_obligations=args.strict_obligations)

    if args.drift:
        _, flagged = drift_report()
        if args.sources:
            return 1 if flagged else 0
        return 0
    if args.sources:
        return run_sources_check()
    return print_validation_report(len(files))
