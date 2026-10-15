# Agent Guide for `law-map`

This file is for AI coding agents working in this repository. It states how
to run the checks and where edits belong. The human-facing contribution
guide is [CONTRIBUTING.md](CONTRIBUTING.md).

## Commands

The `just` task runner drives the common commands:

```sh
just check      # validate + manifest sync + README stats sync + pytest + ruff + mypy + basedpyright
just test
just fmt        # ruff format + ruff check --fix
just validate   # law-map validate only
just pipeline   # validate, then review-freshness check (upstream→downstream order)
just stats      # regenerate the README "Scope today" block from the corpus
just manifest   # regenerate guidance/sections/MANIFEST.yml from section front matter
just drift      # check --sources: freshness + source-URL HEAD probes (network)
just watch      # law-watch: cited instruments amended since review? (network)
```

Run `just fmt` before committing, then `just check` before finishing a
change. If `uv run pytest` fails to resolve the package in your
environment, fall back to `.venv/bin/python -m pytest`. The test suite is
offline; `check --sources` and `watch` probe the network, so do not run
them casually.

Type checking is `mypy --strict` on `src/law_map` plus `basedpyright`
(standard mode, covering `src/law_map` and `tests`); both run as part of
`just check`.

## Where to edit

- Package code: `src/law_map/` (loader, validator, checker, exporter, CLI)
- Obligations: `obligations/<domain>/<slug>.yml` — one obligation per file
- Machine-check specs: `checks/<domain>/<slug>.yml`, optional per obligation
- Guidance prose: `guidance/sections/<tier>/<slug>.md` (CC BY 4.0; see
  `docs/guidance.md`); `MANIFEST.yml` is generated — never edit it by hand;
  `VOCABULARY.yml` is the `when` / `placement` / `status` vocabulary
- Schema: `schemas/obligation.schema.yml` is the field reference; the
  enforceable subset lives in `src/law_map/model.py`
- Tests: `tests/` (offline pytest suite)
- Docs: `README.md` and `docs/`

## Corpus rules (read before editing data files)

Obligation changes start as a [Legal RFC
issue](https://github.com/politeuma/law-map/issues/new?template=legal_rfc.yml)
using the existing template — not as a free-form PR. Wait for the
discussion to settle before writing the change.

- `version` must be `2`. A v1 file names its own fix:
  `law-map migrate --in <v1-obligations> --out <dir>`.
- `id` must match `obligation.<domain>.<slug>`, be unique, and the domain
  must match the directory the file lives in. Files whose basename starts
  with `_` are excluded from the corpus (see `obligations/_example.yml`).
- Every obligation needs at least one `primary` grounding. Every grounding
  needs `jurisdiction` (ISO 3166-1 alpha-2; `EU` is the only exception —
  `UK` is rejected, use `GB`), `source_type`, `source_kind`
  (`primary` means the instrument from its publisher; third-party copies,
  archives, and write-ups are `unofficial`), `status`, `authority`,
  `citation` (pinpoint article/section/case, not a general page),
  ISO `review_by`, and non-empty http(s) `sources`. `subdivision` must be
  an ISO 3166-2 code. Cite the exact legal text — never rely on memory.
- `private_rule` and `incident_report` are not legal sources; never file
  them as `standard` or `precedent`.
- Check specs claiming L2 (release-blocking) need an executable `blocking`
  rule plus existing `fixtures`, one spec per obligation.
  `enforcement.check_refs` entries must point at existing `checks/` files;
  `requires` / `conflicts` must reference ids present in the corpus.
- `related_sections` ids (`<tier>-<slug>`) must resolve against this
  repo's `guidance/` tree (`--kanon <checkout>` checks an external tree
  instead); unreferenced sections warn, unknown ids error.
- Every grounding carries a `review_by` freshness date. Record
  `reviewed_on` when you re-verify a grounding against the instrument's
  current text — never bump `review_by` just to silence the check
  (`law-map check` exits 1 on expired groundings).
- After any corpus change, run `just stats` so the README scope tables
  stay in sync (CI checks them). After touching section front matter, run
  `just manifest` so `MANIFEST.yml` stays in sync (CI checks it too).

## Commits and CI

- Use [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat:`, `fix:`, `docs:`, ...).
- CI runs ruff, mypy, pytest, the README stats sync check, the MANIFEST
  sync check, and `law-map validate` on every push and pull request; keep
  all of them green. The weekly `drift-watch` workflow additionally runs
  the freshness and law-watch scans.
