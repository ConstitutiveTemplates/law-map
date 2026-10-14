---
id: sector-samd-regulatory
version: "2026-10-15.1"
status: active
placement: agents_md
when: medtech
obligations:
  - obligation.ai.samd-clinical-evaluation
triggers:
  keywords: ["samd", "pmda", "fda", "pccp", "clinical", "diagnosis"]
  pattern: '(?i)\b(samd|pmda|fda|pccp|idaten|clinical|diagnos|medical|patient|mdr|ce\s?mark|medical\s?device)\b'
  config: '(?i)\b(patient|clinical|diagnos|pmda|fda|medical)\b'
sources:
  - https://www.fda.gov/regulatory-information/search-fda-guidance-documents/marketing-submission-recommendations-predetermined-change-control-plan-artificial-intelligence
  - https://eur-lex.europa.eu/eli/reg/2017/745/oj
  - https://eur-lex.europa.eu/eli/reg/2024/1689/oj
license: CC-BY-4.0
en:
  title: "Medical SaMD — continuous learning stays inside approved change limits, and humans make the call"
  summary:
    - "Do not swap production models outside an approved change plan (PCCP, IDATEN, ...)."
    - "Default to a structure where a human (clinician) makes the final decision."
    - "Build performance-drift monitoring and post-market surveillance into the initial design."
  prohibited:
    - "Automatic retraining or production model swaps outside the approved scope (updates not in the change plan)."
    - "Diagnoses or treatment decisions finalised automatically without clinician review."
    - "Operating without performance-drift monitoring."
    - "Clinical reliance on unexplained output (scores shown without supporting evidence)."
    - "Designing regulatory requirements to be 'added later' (model management with no audit log or versioning)."
---
# 医療SaMD — 継続学習は承認済み変更限界の中で、判断は人間と共に

> **適用条件**: 診断・治療支援・患者スクリーニング等の医療用途に
> 触れるソフトウェア(医薬品医療機器法上のクラス判定が関わる領域)を
> 設計・学習・更新する場面。
> 規模: 世界問題(患者は法域を問わず被り、規制は日米欧が足並みを
> 揃えつつある)。
> 要約: (1)承認された変更計画(PCCP/IDATEN等)の範囲外で本番モデルを
> 差し替えない (2)最終判断は人間(医師等)が行う構造を既定にする
> (3)性能ドリフトの監視と市販後監視を初期設計に含める。詳細は本文。

## 事実

医療目的のAIソフトウェアは医療機器プログラム(SaMD)として各国当局の
リスク分類と審査を受ける。日本は薬機法のクラスI–IV分類で、
医療機器の変更計画審査体制(IDATEN、厚労省/PMDA)により承認後の
継続的な変更管理が行われる。米国FDAは2024-12、AI-enabled device
software functionsのためのPCCP(Predetermined Change Control Plan)
に関する最終ガイダンスを発行し、開発初期に「将来学習・進化する内容と
変更限界、評価方法」を申請・審査する制度を確立した。欧州はMDRの要件に
加え、EU AI Act(2024-08-01発効)下で高リスクAIシステムの要件が重なり、
CE適合性評価と市販後監視(PMS)が必要になる。AI Actの高リスク義務は
当初2026-08-02一般適用の予定だったが、AI Omnibus(2026-07-27発効)で
延期され、単体の高リスク(附属書III)は2027-12-02、他の規制対象製品
(医療機器等、附属書I)に組み込まれる高リスクシステムは2028-08-02から
適用となる。
出典: FDA PCCPガイダンス、EUR-Lex(MDR/AI Act)(sourcesに記録)。

## 禁止パターン

- 承認範囲外の自動再学習・本番モデル差し替え(変更計画にない更新の
  本番適用)。
- 医師等専門家の確認を経ない診断・治療方針の自動確定。
- 性能ドリフト監視なしの運用(継続学習で性能が変わる前提の監視欠如)。
- 説明可能性を欠く判断への臨床依存(根拠提示なしのスコア表示のみ)。
- 規制要件を「後で足す」設計(監査ログ・バージョン管理なしの
  モデル管理)。

## 推奨設定

- 変更限界の文書化(PCCP風): 想定する再学習の種類、データ条件、
  評価手順、許容する性能変化、ロールバック条件を版管理する。
- シャドウデプロイ+性能モニタリング(本番反映前に現行モデルと
  並行評価し、劣化を検知したら自動で旧版へ)。
- 固定評価データセット(ロック済み)を版管理し、変更ごとに同一基準で
  再評価する。
- 監査ログ(どのモデル版が、どの入力に対し、何を出したか)を残す。
- Human-in-the-Loop UI: 最終判断欄・承認者・根拠提示(ヒートマップ等の
  補助情報)を画面設計に組み込む。
- モデルカード(用途、制限、検証結果)をリリース物に同梱する。

具体例(監査記録と変更限界の判定):

```python
# どの版が、どの入力に、何を出し、誰が確認したかを残す
audit.record(
    model_version=MODEL_VERSION,
    case_ref=case_id,
    output=decision,
    reviewed_by=clinician_id,
)

# 本番差し替えは固定評価セットで再評価し、承認済み変更限界内かで判定する
if not pccp_allows(eval_on_locked_suite(candidate_model)):
    rollback_to(current_model)  # 変更計画の外なら本番に出さない
```

## 運用チェック

- 設定側トリガー(front matter の `triggers.config`)に当たったら、専門家レビューの要否を確認する。
- リリース判定に「変更は承認済み変更計画の範囲内か」を必須項目として
  置く。担当: 品質/規制対応のレビュー役。

## 制度変更ウォッチ

- 変更予告: EU AI Act高リスク義務の適用(AI Omnibusによる延期後、
  単体は2027-12-02、医療機器等への組込み型は2028-08-02)が直近の確定事項。
  確度: 施行済(延期後の日程確定、最終確認: 2026-10-15)。
- 確認TODO: IDATENの公式一次ページ(厚労省)とPCCPの最新Q&Aを確認
  (review_by: 2026-12-18)。
- 影響TODO: 自プロジェクトが医療用途に触れる場合、クラス分類の
  該当性を専門家(薬事コンサル等)に照会する(本節は判断の代行ではない)。

<!-- 法的助言ではない。専門家レビュー必須。 / This is not legal advice; expert review required. -->

<!-- © kanon contributors (https://github.com/politeuma/kanon). Section sector-samd-regulatory, licensed CC BY 4.0: https://creativecommons.org/licenses/by/4.0/ -->
