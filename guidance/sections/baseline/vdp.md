---
id: baseline-vdp
version: "2026-10-06.2"
status: draft
placement: agents_md
when: always
obligations:
  - obligation.security.coordinated-vulnerability-disclosure
triggers:
  keywords: ["security.md", "security.txt", "vdp", "vulnerability disclosure", "bug bounty", "report vulnerability"]
  pattern: '(?i)\b(security\.md|security\.txt|vdp|vulnerability[- ]disclosure|coordinated[- ]disclosure|bug[- ]bounty|report[- ]a[- ]vulnerability)\b'
  config: '(?i)\b(security\.md|security\.txt|vdp|vulnerability[- ]disclosure|bug[- ]bounty)\b'
sources:
  - https://www.cisa.gov/resources-tools/programs/coordinated-vulnerability-disclosure-cvd-program
  - https://www.rfc-editor.org/rfc/rfc9116.html
  - https://www.ipa.go.jp/security/todokede/vuln/uketsuke.html
license: CC-BY-4.0
en:
  title: "Vulnerability disclosure — keep a public channel for external reports"
  summary:
    - "Publish where to report in SECURITY.md or security.txt."
    - "Products for the EU market follow the CRA single reporting platform obligations."
    - "Set handling deadlines (first response, fix, disclosure)."
  prohibited:
    - "Shipping a product or service with no reporting channel ('open an issue' without a defined channel is not enough)."
    - "A SECURITY.md with no contact, form or platform handle (or an unmonitored address)."
    - "A security.txt without a Contact: field."
    - "A channel with no defined handling (response deadline, fix policy, disclosure policy)."
    - "EU-market products operated in disregard of the CRA reporting obligations (single platform, deadlines)."
---
# 脆弱性報告窓口 — 外部からの報告を受ける公開チャネルを持つ

> **適用条件**: 製品・サービスを外部に配布・公開する場面。
> 社内専用ツールで外部の攻撃面がない場合は対象外(ただし社内利用でも
> 委託先からの報告は想定する)。
> 規模: 世界問題(報告の受け皿はどの法域でも必要だが、EU CRA は
> 市場アクセス要件として義務化する)。
> 要約: (1)SECURITY.md か security.txt で報告先を公開する
> (2)EU 市場向け製品は CRA の単一報告基盤の義務に合わせる
> (3)報告の扱い期限(一次応答・修正・公表)を定める。詳細は本文。

## 事実

報告窓口の存在は法域を越えた前提になっている。CISA の BOD 20-01(2020)は
連邦文民機関に脆弱性開示ポリシー(VDP)の公開と運用を義務づけ、民間向けの
CVD ガイダンスが事実上のベースラインになる。IETF RFC 9116(2022)は
`/.well-known/security.txt` の標準形(`Contact:` `Expires:` 欄)を定め、
サービス側の機械可読な窓口として定着した。日本は JVN/JPCERT-CC と IPA の
「情報セキュリティ早期警戒パートナーシップ」(情報処理促進法第23条の
届出制度)が任意の受付枠組みとして機能している。
EU CRA(規則 (EU) 2024/2847)第14条は製造者に協調的脆弱性開示ポリシーの
公開と、能動的悪用・重大インシデントの単一報告基盤への報告を義務づけ、
脆弱性報告の義務は 2026-09-11 から先行適用される(製品全体の義務は 2027-12-11)。
窓口のない製品は CRA の市場アクセス要件に落ちる。
出典: CISA CVD・RFC 9116・IPA 届出制度(sourcesに記録)。

## 禁止パターン

- 配布・公開される製品・サービスに報告チャネルがない(「Issues で適当に」
  も窓口の定義なしでは不十分)。
- SECURITY.md が存在するが報告先(連絡先・フォーム・ platform handle)が
  書かれていない(監視されていないアドレスを含む)。
- security.txt に `Contact:` 欄がない(機械可読の窓口として機能しない)。
- 報告の扱い(一次応答期限・修正方針・公表ポリシー)が未定義のまま窓口だけある。
- EU 市場向け製品で CRA の報告義務(単一基盤・期限)を無視した運用。

## 推奨設定

- リポジトリ直下に SECURITY.md を置く(監視される intake と応答期待を明記)。
- サービスは `/.well-known/security.txt` を配備する(RFC 9116。
  `Contact:` + `Expires:` を必須欄にする)。
- 扱い期限を定める(例: 一次応答 5 営業日以内、修正方針の通知、公表の調整)。
  報告を所有者(owner)に回す経路を持つ。
- EU 市場向け製品は CRA の単一報告基盤の手順と期限(24 時間以内の早期通知等)を
  運用に組み込む(`region-eu-cra` を参照)。
- SBOM との連携: 報告の再現に必要な版・依存の特定ができる状態を保つ
  (CRA 附属書 I Part II の脆弱性対応要件)。

具体例(最小の SECURITY.md):

```markdown
# Security Policy

## 報告窓口
- 脆弱性の報告: security@example.com (PGP: fingerprint ...)
- 一次応答: 5 営業日以内に受領を通知します
- 対象: 本リポジトリの最新リリースと main ブランチ

## 扱い
- 修正方針と公表時期は報告者と調整します
- EU CRA の報告義務が適用される製品は別途の手順に従います
```

## 運用チェック

- 報告窓口の到達性を定期確認する(監視外アドレスの放置を検出)。
  担当: サポート窓口と同じレビュー役。
- 報告の受付→修正→公表の記録を残し、SLA 違反を振り返る。

## 制度変更ウォッチ

- 変更予告: EU CRA の脆弱性報告義務は 2026-09-11 から先行適用
  (製品全体の義務は 2027-12-11)。単一報告基盤の運用詳細は ENISA の
  実装ガイダンスで具体化される。確度: 施行済(スケジュール確定)。
- 確認TODO: ENISA の報告手順ガイダンスの公表を確認
  (review_by: 2027-01-31)。
- 影響TODO: EU 市場向け製品の報告フロー(24 時間早期通知を含む)を
  自プロジェクトの運用に組み込む。

<!-- 法的助言ではない。専門家レビュー必須。 / This is not legal advice; expert review required. -->

<!-- © kanon contributors (https://github.com/politeuma/kanon). Section baseline-vdp, licensed CC BY 4.0: https://creativecommons.org/licenses/by/4.0/ -->
