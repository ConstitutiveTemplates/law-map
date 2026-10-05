# Contributing to law-map

law-map is the obligation graph: machine-readable deontic rules (what
software must do, must not do, or may do) grounded in precise legal sources.
Changes here are reviewed by humans, so they start as issues — not as
free-form PRs.

## Every change starts as a Legal RFC issue

Open a [Legal RFC
issue](https://github.com/ConstitutiveTemplates/law-map/issues/new?template=legal_rfc.yml)
using the existing template. It asks for the jurisdiction, source type,
affected obligation id, the proposed change, a primary source URL, and
reviewer expertise. Wait for the discussion to settle before writing a PR.

## Grounding requirements

Every obligation lives in `obligations/<domain>/<slug>.yml` (one obligation
per file; basenames starting with `_` are excluded from the corpus).
`schemas/obligation.schema.yml` is the field reference; the enforceable
subset lives in `src/law_map/model.py`. What validation actually enforces:

- `version` must equal `1`.
- `id` must match `obligation.<domain>.<slug>` (lowercase alphanumeric
  segments, hyphens allowed), be unique across the corpus, and the domain in
  the id must match the directory the file lives in.
- `title` and `summary` non-empty; `category`, `modality`, `severity` must
  be valid enum values (`privacy, security, copyright, ai, licensing,
  telemetry, crypto` / `obligation, prohibition, permission` / `info,
  advisory, high, critical`).
- `groundings` non-empty; every grounding needs `jurisdiction`,
  `source_type` (`statute, regulation, precedent, guidance, standard,
  model_code`), `status` (`in_force, scheduled, proposed, superseded`),
  `authority`, `citation`, `review_by` (ISO `YYYY-MM-DD`), and a non-empty
  list of `http(s)` URLs in `sources`. `effective` must be an ISO date if
  present.
- `subdivision` is only allowed for jurisdictions `US, CA, AU, DE, GB`;
  anywhere else it is a warning, not an error.
- `enforcement.check_refs` entries must point to existing
  `checks/<domain>/<slug>.yml` files (error otherwise).
- `requires` / `conflicts` must reference ids present in the corpus.
- `related_sections` references good-future-codex section ids
  (`<tier>-<slug>`); unknown ids warn, not error.

Cite the exact legal text — pinpoint article/section/case in `citation`, and
the canonical instrument URL in `sources`. Do not rely on memory.

## Prose lives in good-future-codex

law-map records *what instruments say*; the reviewed, human/AI-facing prose
that tells a team what to do lives in
[good-future-codex](https://github.com/ConstitutiveTemplates/good-future-codex).
An obligation points at its prose via `related_sections`
(`<tier>-<slug>` ids), and `law-map export` produces section skeletons.
Section prose corrections belong there, not here.

## Running the checks

```bash
uv run law-map validate       # corpus rules; exits non-zero on any error
uv run law-map check --sources  # review_by freshness + HEAD-check source URLs
```

`uv run pytest -q` runs the offline test suite. `just check` runs
validate + pytest + ruff + mypy.

## The `review_by` freshness contract

Every grounding carries a `review_by` date — the contract that the map does
not go stale. The weekly `drift-watch` workflow runs
`law-map check --sources --days 30`; a grounding past its `review_by` makes
`check` exit 1, so CI gates on it, and the workflow files/updates a
`law-drift` issue. Never bump a `review_by` just to silence the check —
bump it only after actually re-verifying the source is still current.

## Not legal advice

law-map records what instruments say and where they are pinned; it does not
interpret them for a specific situation. For an actual compliance
determination, consult a qualified practitioner.