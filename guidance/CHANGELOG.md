# Changelog

kanon uses date-based versions, `YYYY.MM.N`: the year and month of the
release, then a counter that starts at 0 each month (`2026.10.0`,
`2026.10.1`, `2026.11.0`, ...). Each release is a git tag of that name with
a GitHub release carrying this file's entry. Consumers may still pin a
commit SHA; the tag names the same commit. Individual sections keep their
own `version: "YYYY-MM-DD.rev"` in front matter, bumped on each content
change.

Breaking changes for consumers are marked **Breaking**.

## 2026.10.0 — unreleased

The first tagged release. It changes the corpus format ahead of the
law-map merge; section content is unchanged apart from the fixes listed.

### Breaking

- Section files are `sections/<tier>/<slug>.md`, no longer `.md.jinja`.
  Ids are unchanged.
- Metadata moved from the `{# ethics: ... #}` comment into YAML front
  matter (`---` … `---`): `id`, `version` (quoted string), `status`,
  `placement`, `when`, `obligations`, `triggers`, `sources`, `license`,
  `en`. The body starts at the `# <title>` line after the closing `---`.
- `triggers` is a mapping: `keywords` (the old header list), `pattern`
  (the regex that was on the body `> Triggers:` line) and `config` (the
  regex from the 運用チェック config-trigger bullet). Those body lines are
  gone; `region-kyushu-ntp`'s plain-word Triggers line is now a regex.
- The `> 配布:` line is gone from every summary blockquote; `when` carries
  the targeting.
- `sections/MANIFEST.yml` is generated (`schema: 2`): it embeds the
  vocabulary, lists rows sorted by file path (the old hand-written order is
  gone) and adds `version`, `status`, `pack`, `obligations` and `triggers`
  to each row. MANIFEST rows no longer carry `sources`.
- The `when` vocabulary is grouped into three axes (distribution form,
  data handled, market) plus unconditional values; `oj_code`, `kaggle` and
  `embedded` live in extension packs (`competitive-programming`,
  `embedded`). Condition names are unchanged. `sections/VOCABULARY.yml` is
  the source.
- Section prose is licensed CC BY 4.0 (`sections/LICENSE`), no longer
  Apache-2.0. Every body ends with an attribution note; keep it when
  rendering. Code stays Apache-2.0.
- kanon's weekly drift-watch workflow and `kanon-drift` issue are gone;
  law-map owns freshness for the obligations each section names.

### Added

- `en:` front matter block per section: English title, summary rules and
  prohibited patterns.
- `obligations:` per section, the law-map obligation ids it serves.
- `tools/manifest.py` / `just manifest`; `just check` and CI fail when
  MANIFEST or the README/CONTRIBUTING vocabulary tables are stale.
- Validator checks for consumer-specific phrases (`REGISTRY.yml`,
  `_shared/`, Copier QA levels, consumer flag names) and retired project
  names in section bodies.

### Fixed

- EU AI Act high-risk dates updated for the AI Omnibus postponement in
  `baseline-personal-data`, `domain-face-recognition`, `domain-ml-bias` and
  `sector-samd-regulatory`.
- 個人情報保護法の漏えい等報告: 2020年改正(2022-04-01施行) — the template
  now asks for 改正年 and 施行日 separately.
- Section bodies no longer refer to a consumer's registry or QA tests.
