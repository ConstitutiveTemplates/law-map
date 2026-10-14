# Contributing to law-map

law-map is the obligation graph: machine-readable deontic rules (what
software must do, must not do, or may do) grounded in precise legal sources.
Changes here are reviewed by humans, so they start as issues — not as
free-form PRs.

## Every change starts as a Legal RFC issue

Open a [Legal RFC
issue](https://github.com/politeuma/law-map/issues/new?template=legal_rfc.yml)
using the existing template. It asks for the jurisdiction, source type,
affected obligation id, the proposed change, a primary source URL, and
reviewer expertise. Wait for the discussion to settle before writing a PR.

## Grounding requirements

Every obligation lives in `obligations/<domain>/<slug>.yml` (one obligation
per file; basenames starting with `_` are excluded from the corpus).
`schemas/obligation.schema.yml` is the field reference; the enforceable
subset lives in `src/law_map/model.py`. What validation actually enforces:

- `version` must equal `2` (v1 files are rejected with a `law-map migrate` prompt).
- `id` must match `obligation.<domain>.<slug>` (lowercase alphanumeric
  segments, hyphens allowed), be unique across the corpus, and the domain in
  the id must match the directory the file lives in.
- `title` and `summary` non-empty; `category`, `modality`, `severity` must
  be valid enum values (`privacy, security, copyright, ai, licensing,
  telemetry, crypto, accessibility` — accessibility law (e.g. the European
  Accessibility Act) has its own category, never `privacy` / `obligation,
  prohibition, permission` / `info, advisory, high, critical`).
- `groundings` non-empty, with at least one `source_kind: primary`;
  every grounding needs `jurisdiction`,
  `source_type` (`statute, regulation, precedent, guidance, standard,
  model_code, private_rule, incident_report`),
  `source_kind` (`primary, official-secondary, unofficial`),
  `status` (`in_force, scheduled, proposed, superseded, withdrawn`),
  `authority`, `citation`, `review_by` (ISO `YYYY-MM-DD`), and a non-empty
  list of `http(s)` URLs in `sources`. `effective` and `reviewed_on` must
  be ISO dates if present.
- `primary` means the instrument from its publisher (gazette, EUR-Lex ELI
  URL, slip opinion). Third-party copies (`dsgvo-gesetz.de`,
  `law.justia.com`), archive snapshots (`web.archive.org`, `*.archives.gov`),
  and write-ups are `unofficial` — claiming otherwise warns.
- `private_rule` (a private body's rules, such as contest terms) and
  `incident_report` (a documented incident whose lesson grounds the
  practice) are not legal sources; never file them as `standard` or
  `precedent`. An obligation grounded only in them lands in the
  `community` pack (see "Packs" in the README).
- Record functional-equivalence differences on the grounding: `scope` (who
  is bound), `exceptions` (carve-outs), `strength` (`binding, persuasive,
  background`), and adverse subsequent history in `negative_history`
  (e.g. the 11th Cir.'s 2018 vacatur of the LabMD order).
- Peer review (`reviewed_by` handle+domain with `reviewed_on`, on the
  obligation and per grounding) is optional; anything lacking it displays
  as `draft`.
- `withdrawn` marks an instrument its authority has rescinded, revoked, or
  taken down (e.g. prior-administration guidance); a source on an archive
  site (`web.archive.org`, `*.archives.gov` subdomains) is a warning.
- `jurisdiction` must be an ISO 3166-1 alpha-2 code (`JP`, `US`, `GB`, ...);
  `EU` is the single documented exception. `UK` is rejected — use `GB`.
- `subdivision` must be an ISO 3166-2 code for its jurisdiction
  (`CA` for `US-CA`), checked via pycountry — not a hardcoded list.
- `L2` check specs need an executable `blocking` rule and existing
  `fixtures`; one obligation, one spec (merge duplicate L1/L2 specs).
- `enforcement.check_refs` entries must point to existing
  `checks/<domain>/<slug>.yml` files (error otherwise).
- `requires` / `conflicts` must reference ids present in the corpus.
- `related_sections` references guidance section ids
  (`<tier>-<slug>`); verified against this repo's `guidance/` tree by
  default (`law-map validate --kanon <checkout>` checks an external tree).

Cite the exact legal text — pinpoint article/section/case in `citation`, and
the canonical instrument URL in `sources`. Do not rely on memory.

## Prose lives in guidance/

law-map records *what instruments say*; the reviewed, human/AI-facing prose
that tells a team what to do lives in `guidance/sections/` (merged here from
the archived [kanon](https://github.com/politeuma/kanon) repo; its history is
preserved via `git subtree`).
An obligation points at its prose via `related_sections`
(`<tier>-<slug>` ids), and `law-map export` produces section skeletons.
Section prose corrections belong in `guidance/sections/<tier>/<slug>.md` —
see [docs/guidance.md](docs/guidance.md) for the layout, the generated
`MANIFEST.yml`, and the freshness contract.

## Running the checks

```bash
uv run law-map validate       # corpus rules + guidance/ cross-checks; exits non-zero on any error
uv run law-map manifest --check  # generated guidance/sections/MANIFEST.yml is in sync
uv run law-map check --sources  # review_by freshness + HEAD-check grounding + section source URLs
```

`uv run pytest -q` runs the offline test suite. `just check` runs
validate + manifest sync + pytest + ruff + mypy + basedpyright.

## The `review_by` freshness contract

Every grounding carries a `review_by` date — the contract that the map does
not go stale. The weekly `drift-watch` workflow runs
`law-map check --sources --days 30`; a grounding past its `review_by` makes
`check` exit 1, so CI gates on it, and the workflow files/updates a
`law-drift` issue. Never bump a `review_by` just to silence the check —
bump it only after actually re-verifying the source is still current.

Record `reviewed_on: "YYYY-MM-DD"` on a grounding when you re-verify it
against the instrument's current text. The weekly law-watch (`law-map
watch`) compares that date with the instrument's latest amendment on
EUR-Lex, e-Gov or legislation.gov.uk and files a `law-watch` issue when the
law changed after it. After any corpus change, run `just stats` so the
README scope tables stay in sync (CI checks them).

## Disclaimer

Not legal advice. Engineering guardrails with citations; ask a qualified
professional for compliance decisions.

法的助言ではありません。出典付きの技術的ガードレールです。コンプライアンスの判断は専門家にご相談ください。

politeuma records what legal sources say and which engineering practices
they support. It does not decide whether your product complies with any
law, and using it does not make anything compliant. Sources can go out of
date or be misread, so every rule shows its sources and the date it was last
checked. Contributors and reviewers share their understanding in good faith;
their contributions are not legal advice to you or anyone else.

politeuma は、法令などの出典が何を定めているか、それがどの技術的な実践を支えるかを記録します。あなたの製品が法律に適合しているかを判断するものではなく、使っただけで適合するものでもありません。出典は古くなったり読み違えたりすることがあるため、すべてのルールに出典と最終確認日を示しています。貢献者やレビュアーは善意で理解を共有していますが、その内容はあなたや他の誰かへの法的助言ではありません。
