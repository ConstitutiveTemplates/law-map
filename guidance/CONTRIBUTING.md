# Contributing to kanon

This repo owns the *content layer* of the ethics/legal stack: reviewed,
versioned prose sections that consumers vendor into generated projects. The
consumer template (architekton-py) does **not** accept section changes — new
sections and corrections to section prose or sources are proposed here.

Issues and PRs in English are welcome. The section bodies are written in
Japanese prose, as the existing ones are (canonical for now); every section
also carries an English `en:` front matter block with its summary and
prohibited patterns.

## What the corpus enforces

Read these before proposing anything:

- `sections/_template.md` — the authoring aid: front matter fields, section
  structure, the fixed 制度変更ウォッチ block and the trailing not-legal-advice
  comment.
- `sections/VOCABULARY.yml` — the `when` / `placement` / `status`
  vocabulary (the table below is generated from it via MANIFEST).
- `sections/baseline/pki-chain.md` — a worked example (front matter, 要約,
  bad/good pairs, review_by dates).
- `tools/validate.py` — what actually gets checked (run it locally; see
  below).

`sections/MANIFEST.yml` is generated — never edit it. Run `just manifest`
after changing any front matter or `VOCABULARY.yml`, and commit the result.

`just check` fails on: missing or malformed front matter (unknown or
missing keys); an `id` that differs from the `<tier>-<slug>` path name; a
`version` that is not a quoted `YYYY-MM-DD.rev`; a `status`, `placement` or
`when` outside `VOCABULARY.yml`; empty `triggers.keywords` or a trigger
regex that does not compile; obligation ids not shaped
`obligation.<category>.<slug>`; empty `sources`; a `license` other than
`CC-BY-4.0`; an `en` block without a title or with empty `summary` /
`prohibited`; a body that does not end with the attribution note for its
own id; template expressions (`{{`/`{%`) in the body; banned phrases
in the body or `en` block (consumer file/flag names such as `REGISTRY.yml`
or `*_effective`, `配布:` / `Triggers:` lines, retired project names); a
missing or out-of-order required heading; an expired `(review_by:
YYYY-MM-DD)` date, or no date at all in a section with no `obligations`;
and a stale MANIFEST or vocabulary table. Dates due within 30 days, and
(when a law-map checkout sits next to this repo) `obligations` that
disagree with law-map's `related_sections`, are warnings. There are no
other checks — describe nothing beyond what the validator enforces.

### `when` vocabulary

<!-- BEGIN GENERATED: when-vocabulary (tools/manifest.py from sections/MANIFEST.yml) -->
| Group | Condition | Meaning | Sections |
| --- | --- | --- | --- |
| Unconditional | `always` | every project that renders the sections | 3 |
| Unconditional | `ai_assisted` | AI coding agents work in the repository | 0 |
| axis: Distribution form | `library` | a library / API package | 1 |
| axis: Distribution form | `cli` | a command-line / terminal tool | 3 |
| axis: Distribution form | `web_api` | an HTTP API or web service | 2 |
| axis: Distribution form | `mcp` | an MCP server or tool-calling agent code | 2 |
| axis: Data handled | `personal_data` | processes personal data | 1 |
| axis: Data handled | `face_recognition` | performs biometric identification or verification | 2 |
| axis: Data handled | `medtech` | medical / SaMD software (clinical decisions or patient data) | 2 |
| axis: Data handled | `scraping` | fetches third-party web content | 1 |
| axis: Data handled | `data_science` | trains or evaluates models on datasets | 2 |
| axis: Market | `commercial` | distributed commercially | 1 |
| axis: Market | `eu_market` | offered on the EU market | 1 |
| axis: Market | `jp` | offered in Japan / operates under Japanese law | 2 |
| extension pack `competitive-programming` | `oj_code` | code submitted to an online judge | 1 |
| extension pack `competitive-programming` | `kaggle` | a data-competition (Kaggle-style) workspace | 1 |
| extension pack `embedded` | `embedded` | embedded / microcontroller firmware | 1 |

`placement`: `agents_md` (the AGENTS.md ethics appendix) / `charter` (a CHARTER.md, for scraping projects) / `legal_md` (a LEGAL.md checklist) / `standalone` (its own file).

`status`: `draft` (written but not yet reviewed; consumers should not render it) / `active` (reviewed; consumers render it when `when` matches).
<!-- END GENERATED: when-vocabulary -->

New conditions go into `VOCABULARY.yml`: on one of the three axes if most
projects can answer the question, otherwise into an extension pack.

## Proposing a new section

1. Copy `sections/_template.md` into the matching tier directory —
   `sections/baseline/`, `domain/`, `region/`, or `sector/` — as
   `sections/<tier>/<slug>.md`.
2. Fill the front matter: `id: <tier>-<slug>` (must match the path name),
   `version: "YYYY-MM-DD.rev"`, `status: draft` (new sections start as
   `draft`; promote to `active` only after review), `placement`, `when`
   from the vocabulary above, the law-map `obligations` the section
   serves, `triggers` (`keywords`, a `pattern` regex, optionally a `config`
   regex), primary-source `sources`, `license: CC-BY-4.0`, and the `en`
   block (English title, summary rules and prohibited patterns).
3. Run `just manifest` to regenerate `sections/MANIFEST.yml`.
4. Write the body consumer-agnostically: never name a consumer's file,
   variable or flag; keep code/config snippets free of `{{ }}` / `{% %}`.
   Cite the primary source as a one-line summary plus link — never paste
   statutes or articles verbatim. Section prose is contributed under
   CC BY 4.0 (`sections/LICENSE`).
5. Keep the required headings in order (## 事実 / ## 禁止パターン /
   ## 推奨設定 / ## 運用チェック / ## 制度変更ウォッチ). Leave a
   `(review_by: YYYY-MM-DD)` date under 制度変更ウォッチ if the section
   has no law-map `obligations`, far enough out that `just check` does not
   warn.
6. Leave the trailing not-legal-advice comment in place if the section
   touches 法域・業法 (the template's comment marks this).
7. End the body with the CC BY 4.0 attribution note from the template,
   with the section's own id.

## Correcting a source or a fact

Fix the prose, the `en` block and/or `sources`, then bump the front matter
`version` to `YYYY-MM-DD.rev` (e.g. `2026-10-06.2`) and run `just manifest`.
The version is the record of the last content change; consumers' sync PRs
diff on it. Never edit a `review_by` date merely to silence the validator —
it is the signal that the section needs a real re-check.

## Running the checks

```bash
just check    # or: uv run --with pyyaml python tools/validate.py (+ pytest)
just manifest # or: uv run --with pyyaml python tools/manifest.py
just drift    # or: uv run --with pyyaml python tools/validate.py --drift
just sources  # or: uv run --with pyyaml python tools/validate.py --sources
```

`just check` exits non-zero on any error. `just drift` reports
due/expired `review_by` dates and probes declared source URLs (curl HEAD
with GET fallback); it always exits 0. `just sources` probes only the
declared `sources:` URLs (front matter, body links, `lang/*.yml`) and exits 1
when any URL is flagged. These are author tools: there is no scheduled
freshness job here — law-map's weekly drift-watch owns review dates and
source liveness for the obligations each section names in `obligations:`.

## What happens downstream

Consumers vendor this repo's sections pinned to a SHA (architekton-py
vendors into `_shared/ethics/`, pinned by `.ethics-vendored`; the
daimonion linter bundles it inside its wheel). Their sync workflow
diffs the pinned SHA against upstream and opens a sync PR for the
maintainer; nothing fetches this repo at render time. So a merged change
here reaches generated projects only after a consumer's sync PR lands.