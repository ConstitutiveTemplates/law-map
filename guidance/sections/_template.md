---
# Section template (an authoring aid; not itself a section). Copy it to
# sections/<tier>/<slug>.md, fill in every field, start as draft, and run
# `just manifest` then `just check`. MANIFEST.yml is generated from this
# front matter -- never edit it by hand.
id: <tier>-<slug>                 # must equal the path: sections/<tier>/<slug>.md
version: "YYYY-MM-DD.rev"         # date of the last content change + revision; quoted
status: draft                     # draft | active (promote only after review)
placement: agents_md              # agents_md | charter | legal_md | standalone
when: always                      # a condition or a list ("any of"); see sections/VOCABULARY.yml
obligations:                      # law-map obligation ids this section serves (law-map owns freshness)
  - obligation.<category>.<slug>
triggers:
  keywords: ["<keyword>"]         # presence-scan keywords
  pattern: '(?i)\b(<regex>)\b'    # code/diff trigger regex
  config: '(?i)\b(<regex>)\b'     # optional: config-file trigger regex
sources:                          # primary citations the section rests on
  - https://<primary-source>
license: CC-BY-4.0                # section prose license (sections/LICENSE)
en:                               # concise English rendering of the summary and prohibited patterns
  title: "<Section title> — <one-line scope>"
  summary:
    - "<rule 1>"
  prohibited:
    - "<prohibited pattern 1>"
---
# <Section title> — <one-line scope>

> **適用条件**: <who must read this, in one paragraph. LLM entry: the first
> five lines decide. If none of the triggers apply, ignore the rest.>
> 規模: <国内問題 / 地域問題 / 世界問題のいずれか + 一行理由>。
> 要約: (1) <rule> (2) <rule> (3) <rule>. 詳細は本文。

## 事実

<What happened, with numbers. Cite the primary source inline; do not copy
statutes or articles verbatim — one-line summary plus link.
法改正は「改正年」と「施行日」を分けて書く: 改正年は改正法の成立(公布)年、
施行日はその規定が効力を持つ日。例: 「2020年改正(2022-04-01施行)」。
施行日だけを改正年として書かない(誤:「2022年改正」)。>

## 禁止パターン

<What must not be generated or configured. Concrete shapes, not slogans.
At least one bad/good code-or-config pair: the reader must be able to
pattern-match their own code against it.>

## 推奨設定

<Copy-pasteable configuration or code sketch with versioned defaults.
Show the bad shape next to the good one where it helps; keep snippets
free of `{{ }}` / `{% %}` (consumers may wrap the section in a template engine).>

## 運用チェック

<Monitoring, sunset plan, review cadence. Name the owner role.
Config/code trigger regexes go in the front matter `triggers`, not here.>

## 制度変更ウォッチ

- 変更予告: <one line + source + 確度: 報道/審議中/法案/施行済
  (最終確認: YYYY-MM-DD)>
- 確認TODO: 一次ソースで○○を確認 (review_by: YYYY-MM-DD)
  (review_by は obligations を持たない節では必須。持つ節の鮮度は law-map が追う)
- 影響TODO: <cost / contract / procedure deltas>

<!-- 法域・業法に触れる節は下の定型免責を残す。法的助言ではない。
     専門家レビュー必須。 / This is not legal advice; expert review required. -->

<!-- Keep the license note below as the last line; the id must match the front matter. -->
<!-- © kanon contributors (https://github.com/politeuma/kanon). Section <tier>-<slug>, licensed CC BY 4.0: https://creativecommons.org/licenses/by/4.0/ -->
