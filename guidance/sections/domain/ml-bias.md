---
id: domain-ml-bias
version: "2026-10-15.1"
status: active
placement: agents_md
when: [data_science, kaggle]
obligations:
  - obligation.ai.ml-bias-mitigation
triggers:
  keywords: ["fairness", "bias", "subgroup", "xai", "demographic"]
  pattern: '(?i)\b(fairness|bias|demographic|subgroup|shap|xai|explainab|protected|disparate|equalized|parity)\b'
  config: '(?i)\b(fairlearn|shap|groupby\(.*(race|gender|age|sex)|fairness|subgroup)\b'
sources:
  - https://www.nejm.org/doi/full/10.1056/NEJMc1919366
  - https://eur-lex.europa.eu/eli/reg/2024/1689/oj
license: CC-BY-4.0
en:
  title: "ML bias — build per-group evaluation, explainability and human review into evaluation"
  summary:
    - "Always report per-group performance, not just average accuracy."
    - "Dropping protected attributes does not remove discrimination; handle proxies."
    - "Require human review for decisions that affect life opportunities."
  prohibited:
    - "Treating a dropped protected-attribute column (race, sex, age, ...) as the fix while proxies (postcode, hospital ID, ...) restore it."
    - "Reporting only average accuracy (no per-group sensitivity, specificity or FPR)."
    - "Fully automated decisions without human review in medicine, employment, lending or law enforcement."
    - "Choosing fairness metrics undocumented (metric changes without review)."
    - "Leaking evaluation data into training data (making per-group evaluation impossible)."
---
# MLバイアス — 集団別評価・説明可能性・人間確認を評価に組み込む

> **適用条件**: モデル学習・評価パイプライン、スクリーニング/判定
> ロジック、データセット構築で、人に関する予測や判断を扱う場面。
> 人について自動的に決める場合(評価・順位付け・承認・審査・照合)は、
> 精度の高低にかかわらず本節の対象。
> 規模: 世界問題(偏ったデータはどの国の集団にも不利に働き得る)。
> 要約: (1)平均精度だけでなく集団別の性能を必ず出す (2)protected
> attributeのdropだけで差別を消したことにはしない(proxy対策)
> (3)生命機会に影響する判断は人間確認を必須にする。詳細は本文。

## 事実

学習データの集団偏りは実害として報告されている。経皮的動脈血酸素飽和度
計(パルスオキシメータ)では、黒人患者で「実は低酸素なのに計測値が
正常を示す」見えない低酸素血症の頻度が約3倍になるという分析が
2020年に報告され、デバイス・データ収集の偏りが臨床判断の歪みに
直結する例とされた。EU AI Act(2024-08-01発効)は高リスクAIの
学習/検証/テストデータにバイアス観点での検査と、関係する代表性を
要求し(第10条)、展開者への基本的権利影響評価(FRIA)も定める。
fairness指標は相互に両立しないことが数学的に示されているため、
「どの指標を選んだか、何を捨てたか」の文書化が実務上の最低要件になる。
出典: Sjoding et al. (NEJM 2020)、EU AI Act(sourcesに記録)。

## 禁止パターン

- protected attribute(人種・性別・年齢等)の列dropだけで対処完了と
  する設計(proxy変数(郵便番号、病院ID等)が実質復元する)。
- 平均精度だけの報告(集団別sensitivity/specificity/FPRを出さない)。
- 生命機会(医療、雇用、融資、法執行)での自動確定(人間確認なしの
  単独判断)。
- fairness指標の無文書選択(指標変更がレビューなしで行われる)。
- 評価データの学習データへの混入(集団別評価を不能にする)。

## 推奨設定

- 評価レポートの既定形に集団別表を含める(サブグループ ×
  sensitivity/specificity/FPR。サンプル小集団は区間表示で出す)。
- 指標選択の文書化(demographic parity と equalized odds は通常両立
  しない。選んだ指標と捨てた指標をREADME/モデルカードに明記)。
- 説明可能性: SHAP等のfeature attributionをレビュー工程に置き、
  proxy由来の重み変数を点検する。
- データセットにdatasheet(収集方法・人口構成・既知の偏り)を添付する。
- 分布ドリフトの監視と再評価トリガーを設け、性能の維持を前提にしない。
- 最終判断は人間(専門家)が行うUI/フローを既定にする。

具体例(集団別評価の既定出力):

```python
# 平均だけを出さない: 集団別表は評価パイプラインの標準成果物にする
for group, rows in eval_df.groupby(["race", "sex"]):
    subgroup_metrics[group] = sensitivity_specificity_fpr(rows)
# 小さい集団は点推定だけにしない: bootstrap の 95% 区間を添える
intervals = bootstrap_ci(eval_df, group_cols=["race", "sex"], n=1000)
write_model_card(subgroup_metrics, intervals)  # リリース物に同梱する
```

## 運用チェック

- モデルリリースのチェックリストに「集団別表の添付」「指標選択の
  文書」を置く。担当: 実験レビュー役。

## 制度変更ウォッチ

- 変更予告: EU AI Actの高リスク義務は段階適用。当初の日程
  (2026-08-02一般適用、製品組込み型は2027-08-02)はAI Omnibus
  (2026-07-27発効)で延期され、単体の高リスク(附属書III)は2027-12-02、
  他の規制対象製品に組み込まれる高リスク(附属書I)は2028-08-02から適用。
  確度: 施行済(延期後のスケジュール確定、最終確認: 2026-10-15)。
- 確認TODO: 第10条・FRIAの実務ガイダンス(委員会ガイドライン)の公表を確認
  (review_by: 2026-12-18)。
- 影響TODO: 自プロジェクトの評価レポートテンプレートに集団別表を
  組み込む。

<!-- 法的助言ではない。専門家レビュー必須。 / This is not legal advice; expert review required. -->

<!-- © kanon contributors (https://github.com/politeuma/kanon). Section domain-ml-bias, licensed CC BY 4.0: https://creativecommons.org/licenses/by/4.0/ -->
