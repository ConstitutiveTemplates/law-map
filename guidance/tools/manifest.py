#!/usr/bin/env python3
"""Regenerate sections/MANIFEST.yml and the README/CONTRIBUTING vocabulary tables.

Run:  uv run --with pyyaml python tools/manifest.py          # write
      uv run --with pyyaml python tools/manifest.py --check  # exit 1 when stale
"""

from __future__ import annotations

import argparse
import sys

from validation.const import REPO
from validation.manifest import expected_outputs, stale_outputs, write_outputs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="do not write; exit 1 when any output is stale")
    args = parser.parse_args(argv)
    outputs = expected_outputs()
    if args.check:
        stale = stale_outputs(outputs)
        for path in stale:
            print(f"stale: {path.relative_to(REPO)} (run `just manifest`)", file=sys.stderr)
        if not stale:
            print(f"ok: {len(outputs)} generated file(s) in sync")
        return 1 if stale else 0
    for path in write_outputs(outputs):
        print(f"wrote {path.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
