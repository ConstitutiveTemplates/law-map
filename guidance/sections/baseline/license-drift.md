---
id: baseline-license-drift
version: "2026-09-21.1"
status: active
placement: agents_md
when: always
obligations:
  - obligation.licensing.no-copyleft-contamination
  - obligation.security.sbom-and-vulnerability-handling
triggers:
  keywords: ["license", "bsl", "sspl", "copyleft", "gpl", "terraform"]
  pattern: '(?i)\b(licen[cs]e|bsl|busl|sspl|rsal|elv2|copyleft|gpl|agpl|lgpl|terraform|opentofu|elasticsearch|redis|source-available)\b'
  config: '(?i)\b(BUSL|SSPL|RSAL|ELv2|licen[cs]e)\b'
sources:
  - https://www.hashicorp.com/blog/terraform-is-now-source-available
  - https://opentofu.org/faq/
license: CC-BY-4.0
en:
  title: "License drift — track each dependency's current license and keep BSL/SSPL out"
  summary:
    - "Check the current license when adding a dependency and match it against an allowlist."
    - "Do not let source-available licenses such as BSL/SSPL in without review."
    - "When a project forks (Terraform to OpenTofu, ...), move to the legitimate successor."
  prohibited:
    - "Adding dependencies without a license check (source-available BSL/SSPL/RSAL/ELv2, or missed strong copyleft)."
    - "Confusing fork origin and fork (e.g. listing upstream Terraform as MPL 2.0, or OpenTofu as BUSL)."
    - "Pinning old versions on the assumption 'it was OSS when we added it' without re-checking licenses on updates."
    - "Fabricated license statements in README or NOTICE that do not match reality."
---
# ライセンス変動 — 依存の現行ライセンスを追跡し、BSL/SSPL混入を防ぐ

> **適用条件**: 依存パッケージ・ツールチェーン・コンテナイメージを
> 追加・更新する場面すべて。フォーク元が非OSS化した事例の引用も含む。
> 規模: 世界問題(ライセンス変更はどの法域でも起き、汚染は世界の
> リポジトリに広がる)。
> 要約: (1)追加時に現行ライセンスを確認し、allowlistと照合する
> (2)BSL/SSPL等のソース可用ライセンスを確認なしで混入させない
> (3)フォーク移行(Terraform→OpenTofu等)は正当な後継を通す。
> 詳細は本文。

## 事実

HashiCorpは2023-08-10、TerraformをMPL 2.0からBusiness Source License
(BUSL 1.1)へ変更した。コミュニティはフォークOpenTofuを設立し、
Linux Foundation傘下で継続している。2024-04にHashiCorpはOpenTofuに対し
BSL適用後コードの不正利用を主張する書簡を送付し、OpenTofuは公開で反論した
(MPL 2.0版のコードに基づくとする立場。係争は公開記録の範囲で確認できる)。
方向が逆の例もある: Elasticは2024-08にElasticsearchへAGPLv3を
追加選択肢として復帰させ、Redisも2025-05にAGPLv3を追加した。
つまり依存のライセンスは「追加時点の記憶」では正しくなく、
リポジトリ単位で変動する。BUSL自体は発行からChange Date(原則4年)経過で
指定ライセンスへ切り替わるため、版ごとに扱いが変わる点にも注意する。
出典: HashiCorp公式ブログ、OpenTofu FAQ(sourcesに記録)。

## 禁止パターン

- ライセンス確認なしの依存追加(BSL/SSPL/RSAL/ELv2等のソース可用、
  強copyleftの確認漏れ)。
- フォーク元・フォーク先の取り違え(Terraform本家をMPL 2.0と誤記載、
  OpenTofuをBUSLと誤記載)。
- 「昔追加したからOSSのはず」という版の据え置き(renovateやlock更新で
  ライセンス欄を再確認しない運用)。
- ライセンス表示の捏造(README/NOTICEに実態と異なる表記)。

## 推奨設定

- allowlist方針を明文化(Apache-2.0/MIT/BSD/MPL-2.0等を許可、
  GPL系は配布形態照合、BSL/SSPLは例外承認制)。明文化の雛形:
  ```text
  許可: Apache-2.0 / MIT / BSD-2・3-Clause / ISC / MPL-2.0 / Python-2.0 / Unlicense
  要照合: LGPL(リンク形態) / EPL-2.0(例外条項の範囲)
  原則拒否・例外承認制: GPL系(配布形態照合) / AGPL / BSL / SSPL / RSAL / ELv2
  ```
- 依存ライセンスの列挙と照合は、生成物に同梱の `license-check` タスクが
  行う(`pip-licenses --from=mixed --partial-match`。security推奨で有効、
  CIのlintジョブから呼ばれる。fail-on はプロジェクトのライセンスから
  自動導出: permissive/Proprietary等→GPL系(LGPL/AGPL含む)、
  GPL/LGPL→AGPL、AGPL→なし=最強なので打ち止め)。質問票が提示する
  全ライセンスがポリシーに解決される(取りこぼすと「絶対に落ちない
  license-check」が同梱され、本節の L2 主張が嘘になる)。`--partial-match` は
  部分一致なので、`GPL` は `GNU General Public License (GPLv3)` /
  `...(LGPL)` / `...(AGPLv3)` のいずれにも当たる。タスクを落とした
  構成では同型の照合(`pip-licenses`相当でlicense欄を出力しallowlistと照合)を
  自前で組む。
- renovate等の自動更新でメジャー更新・ライセンス欄変化を通知対象にする。
- 競合サービスを作る予定がある場合、SSPL/BSL類は「自分が提供する形」で
  制限に触れるため、早期に弁護士照会(本節はその判断の代行ではない)。

## 運用チェック

- 依存のライセンス棚卸しを半期に一度、pyproject/lockの差分レビューで
  実施する。担当: 依存管理と同じレビュー役。

## 制度変更ウォッチ

- 変更予告: HashiCorpとOpenTofuの係争は動き得る。確度: 係争中(公開記録)。
  Elastic/Redisの復帰のように逆方向の変更もあり得る。
- 確認TODO: OpenTofu FAQとHashiCorp公式の現行方針を一次で確認
  (review_by: 2027-03-31)。
- 影響TODO: 自プロジェクトがTerraform/OpenTofu類のツールを参照する場合、
  どちらを後継として扱うかドキュメントに明記する。

<!-- 法的助言ではない。専門家レビュー必須。 / This is not legal advice; expert review required. -->

<!-- © kanon contributors (https://github.com/politeuma/kanon). Section baseline-license-drift, licensed CC BY 4.0: https://creativecommons.org/licenses/by/4.0/ -->
