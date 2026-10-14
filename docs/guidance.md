# Guidance sections: the rulebook prose

law-map is **the rulebook**: obligations (`obligations/`) + guidance sections
(`guidance/sections/`) + check specs (`checks/`). One rule = an **obligation**
(the deontic requirement and its legal groundings) + optional **guidance**
(reviewed prose that tells a team what to do) + optional **check spec**
(the machine check that enforces it). This note covers the guidance third:
layout, the generated `MANIFEST.yml`, the freshness contract (KN-11), and
where consumers (daimonion, architekton-py) must look.

The canonical diagram of how the repositories fit together is
[politeuma/.github `profile/diagram.md`](https://github.com/politeuma/.github/blob/main/profile/diagram.md).
The sections were merged here from the archived
[kanon](https://github.com/politeuma/kanon) repo via `git subtree`
(`git log --follow guidance/sections/...` shows the kanon history).

## Layout

Sections live under `guidance/sections/` (tiers chosen, documented here —
`baseline/`, `domain/`, `region/`, `sector/`, plus `lang/` data files):

```
guidance/sections/<tier>/<slug>.md   one section per file; id = <tier>-<slug> from the path
guidance/sections/MANIFEST.yml       GENERATED index (do not edit; `law-map manifest`)
guidance/sections/VOCABULARY.yml     `when` / `placement` / `status` vocabulary (source of truth)
guidance/sections/_template.md       authoring aid (not a section)
guidance/sections/LICENSE            CC BY 4.0 legal code for the section prose
guidance/sections/lang/*.yml        shared language data (e.g. copyright terms)
guidance/tools/                      section validation + manifest tooling (kanon heritage)
```

Section front matter (YAML `---` block) carries exactly: `id`, `version`
(quoted `"YYYY-MM-DD.rev"`), `status` (`draft` | `active`), `placement`
(`agents_md` | `charter` | `legal_md` | `standalone`), `when` (a condition or
list from `VOCABULARY.yml`), `obligations` (law-map obligation ids the section
serves), `triggers` (`keywords` / `pattern` / `config` regexes), `sources`
(non-empty http(s) URLs), `license` (`CC-BY-4.0`), `en` (`title` / `summary[]` /
`prohibited[]`). The body opens with `# <title>` and keeps the required
headings in order (`## 事実 / ## 禁止パターン / ## 推奨設定 / ## 運用チェック /
## 制度変更ウォッチ`), ends with the CC BY 4.0 attribution note, and stays
consumer-agnostic (no template expressions, no consumer names).

## MANIFEST.yml

`guidance/sections/MANIFEST.yml` (`schema: 2`) is a **generated artifact**,
checked in: the embedded vocabulary plus one row per section (`id`, `file`,
`version`, `status`, `placement`, `when`, `pack`, `obligations`, `triggers`).
Prose fields (`en`, `sources`) stay in the section file.

- Regenerate: `law-map manifest` (thin adapter over
  `guidance/tools/validation/manifest.py`; byte-identical to
  `python guidance/tools/manifest.py`). The kanon-era vocabulary-table
  regeneration into README/CONTRIBUTING is retired — those docs are gone with
  the kanon repo infra; the vocabulary lives in `VOCABULARY.yml` and is
  embedded in the MANIFEST.
- Verify: `law-map manifest --check` (wired into `just check` and CI).
- Section changes that touch front matter MUST regenerate the MANIFEST in the
  same commit.

## obligation <-> section mapping

Both directions are checked; together they keep the links exact:

| direction | where | rule |
| --- | --- | --- |
| obligation → section | `obligations/*/*.yml` `related_sections:` | every `<tier>-<slug>` id must resolve to `guidance/sections/<tier>/<slug>.md` — **error** on unresolved ids (`law-map validate`, checked against `guidance/` by default; `--kanon <checkout>` for an external tree). Unreferenced sections become **warnings** (reverse coverage), never errors. |
| section → obligation | `guidance/sections/*/*.md` front matter `obligations:` | every id must match `obligation.<category>.<slug>` (**error** on bad shape); ids with no `obligations/<domain>/<slug>.yml` **warn**, and **error** in strict mode (`guidance/tools/validate.py --strict-obligations`, also run by drift-watch). Disagreement between the two directions warns. |

## Freshness (KN-11): sections keep `review_by`, law-map owns the watch

Sections keep their `(review_by: YYYY-MM-DD)` dates in `## 制度変更ウォッチ`,
but **law-map owns the watch** — one system, not two:

- A section that lists law-map `obligations:` needs no `review_by` of its own
  (law-map's `review_by` per grounding owns its freshness); dates that are
  present are still checked (expired = stale claim). A section with no
  obligations must carry at least one date.
- `law-map check --sources` HEAD-probes grounding `sources:` **and** guidance
  section `sources:` together (deduped; `src/law_map/sources.py`).
- `law-map watch` covers section instruments too: EUR-Lex / e-Gov /
  legislation.gov.uk URLs found in section `sources:` are compared against
  the publisher feeds, baselined on the section front matter `version` date.
  Section hits render as `[law-watch changed] <section-id> section
  <kind>:<instrument>`. See `src/law_map/watch.py`
  (`collect_section_watch_refs`, `guidance_section_refs`).
- The weekly drift-watch workflow runs all three (`check --sources`,
  `validate`, guidance `validate.py --strict-obligations`) and files one
  `law-drift` / `law-watch` issue.

## Where consumers must look

For daimonion / architekton-py (and any future renderer):

- **Discovery**: read `guidance/sections/MANIFEST.yml`. Each row gives the
  section `id`, the `file` path relative to `guidance/sections/`
  (e.g. `baseline/pki-chain.md`), `version`, `status` (render only `active`),
  `placement` (where the prose lands: `agents_md` | `charter` | `legal_md` |
  `standalone`), `when` (abstract conditions from `VOCABULARY.yml` — map each
  to your own gating; never match flag names), `pack` (`core` or the
  extension pack whose conditions alone gate the section), `obligations`
  (the law-map obligation ids the section serves), and `triggers`
  (`keywords` list, `pattern` and `config` regexes for detection).
- **Prose**: parse the section file's front matter for metadata, render the
  Markdown body after the closing `---`. The `en:` block (`title`,
  `summary[]`, `prohibited[]`) is the English machine-readable abstract.
- **Freshness**: `obligations` rows point at `obligations/<domain>/<slug>.yml`
  groundings (each with `review_by` / `reviewed_on`); section `sources:`
  URLs are the cited evidence. Re-verify against the section's obligations
  and `sources:` when the watch reports a change.
- **License**: section prose is CC BY 4.0 (`guidance/sections/LICENSE`);
  keep the trailing attribution note when pasting prose.
