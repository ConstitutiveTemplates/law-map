# Tooling differences from sibling repos (LM-12)

law-map shares a Python floor with open-law and architekton-py but does
not copy their full toolchain. The differences below are deliberate. Revisit
them when one of the stated reasons stops holding; do not "fix" them one by
one to match a sibling.

| aspect | law-map | open-law | architekton-py | daimonion |
| --- | --- | --- | --- | --- |
| `requires-python` | `>=3.11` | `>=3.11` | `>=3.11` | `>=3.11` |
| build backend | hatchling, static `version` | setuptools + setuptools-scm | setuptools + setuptools_scm | hatchling, static `version` |
| CLI framework | stdlib `argparse` | stdlib `argparse` | typer (in generated projects) | stdlib `argparse` |
| type checkers | mypy `strict` (gate) + basedpyright `standard` | basedpyright + pyrefly | basedpyright + pyrefly | none |
| lint | ruff | ruff (large rule set) | ruff (large rule set) | ruff |

## requires-python: aligned

Was `>=3.10`; now `>=3.11`, same as every sibling. mypy, basedpyright,
and ruff all target 3.11, and CI runs 3.12. No difference left to keep.

## Build backend: hatchling with a static version

- law-map is a data repo with a small validator CLI, consumed as a git
  checkout (`law-map validate`, drift-watch) and not published to PyPI.
  A version from git tags (setuptools-scm) has no consumer here.
- setuptools-scm needs git metadata at build time. open-law carries a
  `fallback_version` workaround for that; a static version needs none.
- hatchling matches daimonion, the other rulebook-side repo, and builds
  `src/law_map` with one `[tool.hatch.build.targets.wheel]` line.

Switch to setuptools-scm if law-map starts publishing releases that
consumers pin by version.

## CLI: argparse, not typer

- typer is in the architekton-py *generated-project* template (the ML
  pipeline scripts). None of the sibling *tool* repos use it: open-law
  and daimonion both use `argparse`.
- argparse keeps the runtime dependencies at `pyyaml`, `httpx`, and
  `pycountry` (open-law stays an optional extra), so installing the
  validator in CI pulls in nothing else.
- The subcommands (`validate`, `list`, `show`, `check`, `stats`, `export`,
  `migrate`, `record-hashes`, `manifest`, `watch`) form one flat level;
  typer's annotation-driven parsing would add a dependency without
  simplifying them.

## Type checking: mypy strict plus basedpyright

- `basedpyright` uses open-law's settings (`standard` mode, Python 3.11),
  so code moved between the two repos type-checks the same way.
- mypy `strict` stays as the stricter gate on `src/law_map`; most of the
  code handles YAML-loaded `dict[str, Any]` documents, where strict mode's
  `Any` checks earn their keep. pyrefly is not added; two checkers are
  enough for a codebase this size.

## Keeping this current

When a sibling changes its floor, backend, CLI, or checkers, update the
table above in the same PR that reacts to it (or that decides not to).
