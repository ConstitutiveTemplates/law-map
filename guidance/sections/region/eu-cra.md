---
id: region-eu-cra
version: "2026-10-04.1"
status: active
placement: agents_md
when: commercial
obligations:
  - obligation.security.coordinated-vulnerability-disclosure
  - obligation.security.sbom-and-vulnerability-handling
triggers:
  keywords: ["cra", "sbom", "vulnerability", "cve", "incident", "resilience"]
  pattern: '(?i)\b(cra|sbom|cyclonedx|vulnerability|vulnerabilities|cve|incident[_ ]?report|resilience|enisa)\b'
  config: '(?i)\b(sbom|cyclonedx|vulnerability_report|security_txt|incident_report|cra_)\b'
sources:
  - https://eur-lex.europa.eu/eli/reg/2024/2847/oj
  - https://digital-strategy.ec.europa.eu/en/policies/cra-reporting
license: CC-BY-4.0
en:
  title: "EU CRA — vulnerability reporting and SBOMs are no longer optional for commercial software"
  summary:
    - "Report actively exploited vulnerabilities within 24 hours of becoming aware."
    - "Produce an SBOM so you can account for where every dependency came from."
    - "State the support period and ship security updates throughout it."
  prohibited:
    - "Shipping a product with no vulnerability disclosure contact."
    - "No SBOM and no way to say which version of which library is bundled."
    - "Offering a product without deciding its support period."
    - "Assuming the open-source exemption still applies after commercialisation (misreading Article 24)."
    - "Holding the report until a fix exists (the 24-hour early warning does not wait for a fix)."
    - "Not monitoring dependency vulnerabilities continuously (e.g. pip-audit not in CI)."
---
# EU CRA — 商用ソフトの脆弱性報告とSBOMは、もう任意ではない

> **適用条件**: ソフトウェアを EU 市場に提供する(販売・有償サービス・
> 商用製品への組込み)場面。無償のオープンソースであっても商用化した
> 時点で対象になる。社内利用のみ、非商用の公開は対象外。
> 規模: 地域問題(義務は EU 市場に提供する製造者に課され、
> 域外の開発者も対象になる)。
> 要約: (1)脆弱性の能動的悪用を知ったら24時間以内に報告する
> (2)SBOM(部品表)を作り、依存の出所を説明できるようにする
> (3)サポート期間を明示し、その間はセキュリティ更新を出す。
> 詳細は本文。

## 事実

EU のサイバーレジリエンス規則(Cyber Resilience Act、規則 (EU) 2024/2847)
は、デジタル要素を持つ製品の製造者に水平な(業種を問わない)サイバー
セキュリティ要件を課す。2024-12-10 に発効し、**段階的に適用される**:
適合性評価機関の通知規定は 2024-06-11 から、報告義務は **2026-09-11**
から、主たる義務は 2027-12-11 から。

開発者にとって効くのは主に次の三点である。第一に、**能動的に悪用されて
いる脆弱性と重大インシデントの報告**: 認識から24時間以内の早期警告、
72時間以内の詳細、脆弱性の場合は14日以内の最終報告を、ENISA の単一
報告プラットフォーム経由で行う(第14条)。第二に、**ソフトウェア部品表
(SBOM)** を含む技術文書の作成と、サポート期間中のセキュリティ更新の
提供(附属書I)。第三に、**適合性評価と CE マーキング**。

重要な留保が二つある。第一に、**オープンソース免除は非商用に限られる**
(第24条)。自由・オープンソースソフトウェアは原則として製造者義務の
外にあるが、商業活動として提供された場合は対象に戻る。第二に、
**報告義務は既に発動しており、市場に置いた時期を問わない**。2027年まで
猶予があるという理解は誤りで、2026-09-11 以降に悪用を認識した時点で
報告義務が生じる。出典: 規則 (EU) 2024/2847(sourcesに記録)。

## 禁止パターン

- 脆弱性開示の窓口が無い(連絡先不明のまま製品を出す)。
- SBOM を持たず、依存の出所を説明できない(どのライブラリのどの版を
  同梱したかが言えない)。
- サポート期間を決めずに提供を始める(更新を出し続ける約束のないまま
  市場に置く)。
- 商用化した後もオープンソース免除を前提にする(第24条の誤解)。
- 報告を「修正ができてから」に回す(24時間の早期警告は修正を待たない)。
- 依存の脆弱性を継続的に監視していない(既存の `pip-audit` を CI に
  入れずに運用する)。

## 推奨設定

- SBOM を機械的に生成する: `cyclonedx-py` などで CI で生成し、リリース
  成果物に同梱する(手書きにしない。drift の原因になる)。
- 依存の脆弱性監視を CI に置く(このテンプレートの `audit` タスクが
  該当。`pip-audit` を定期実行する)。
- `SECURITY.md` に報告窓口と対応方針を書き、連絡先を実在させる。
- サポート期間を `pyproject.toml` か README に明記し、その期間は更新を
  出す前提でリリース計画を立てる。
- 24時間報告の手順を文書化する(誰が、どこに、何を知った時点で)。
  実際の報告先は ENISA の単一報告プラットフォーム。
- 商用化の判断時に、非商用だった構成のままかを確認する(依存の
  ライセンスと同様、`distribution` の回答が変われば義務も変わる)。

具体例(報告の流れ。第14条。2026-09-11 以降は適用済み):

```text
1) 能動的悪用を認識 → 24h 以内に ENISA へ早期警告(未確定でも出す)
2) 72h 以内に詳細報告(影響範囲・既知対策の状況)
3) 脆弱性は 14 日以内に最終報告(修正版の有無を含む)
```
窓口と担当者を `SECURITY.md` に書き、この手順自体を版管理する。

## 運用チェック

- 設定側トリガー(front matter の `triggers.config`)に当たったら、SBOM 生成と報告手順の有無を確認する。
- リリース判定に「SBOM が添付されているか」「サポート期間が明示されて
  いるか」を必須項目として置く。担当: リリース責任者。

## 制度変更ウォッチ

- 変更予告: 主たる義務の適用が **2027-12-11**。報告義務は適用済
  (2026-09-11)。確度: 施行済(日程確定)。
- 確認TODO: ENISA の単一報告プラットフォームの稼働状況と、欧州委員会の
  実務ガイダンスの追加公表を確認する(review_by: 2027-03-31)。
- 影響TODO: `distribution` に commercial を選んだプロジェクトは、SBOM
  生成タスクとサポート期間の明示を実際に足す。

<!-- 法的助言ではない。専門家レビュー必須。 / This is not legal advice; expert review required. -->

<!-- © kanon contributors (https://github.com/politeuma/kanon). Section region-eu-cra, licensed CC BY 4.0: https://creativecommons.org/licenses/by/4.0/ -->
