---
id: domain-face-recognition
version: "2026-10-15.1"
status: active
placement: agents_md
when: face_recognition
obligations:
  - obligation.ai.biometric-identification-gated
triggers:
  keywords: ["face", "facial", "biometric", "recognition", "bipa", "liveness"]
  pattern: '(?i)\b(face|facial|biometric|biometrics|faceid|face_id|liveness|deepfake|recognition|arcface|insightface|retinaface)\b'
  config: '(?i)\b(face|facial|biometric|liveness|arcface|insightface|retinaface|deepface)\b'
sources:
  - https://www.nist.gov/publications/face-recognition-vendor-test-part-3-demographic-effects
  - https://eur-lex.europa.eu/eli/reg/2024/1689/oj
  - https://web.archive.org/web/20250630192313/https://www.ilga.gov/legislation/ilcs/ilcs3.asp?ActID=3004
  - https://eur-lex.europa.eu/eli/reg/2016/679/oj
license: CC-BY-4.0
en:
  title: "Face recognition — biometric identification is an exception; confirm the use is lawful first"
  summary:
    - "Confirm the use is lawful before implementing; if it is a prohibited use, do not write the code."
    - "Handle biometric templates in a non-reversible form, with consent and deletion paths."
    - "Measure accuracy per demographic group; do not default to a single threshold."
  prohibited:
    - "Building prohibited uses (EU AI Act Article 5 uses, or surveillance banned in the jurisdiction), including implementing before the lawfulness check."
    - "Building databases by untargeted scraping (collecting face images without consent or robots/terms checks)."
    - "Storing biometric templates reversibly (keeping, logging or sharing them in a form that can restore the original image)."
    - "Matching on a single threshold without measuring per-group error rates."
    - "Matching without consent (continuous matching or tracking with no opt-out)."
    - "No erasure path on deletion requests (templates, derived embeddings or caches left behind)."
    - "Treating attribute estimation (age, gender, emotion, ethnicity) as if it were identification (it is error-prone and banned for some uses)."
---
# 顔認識 — 生体識別は例外手続き、用途の適法性を先に確認する

> **適用条件**: 顔画像から個人を識別・検証・属性推定する
> コード(検出、embedding抽出、照合、liveness判定、属性分類)を
> 書く・学習させる・組み込む場面。
> 規模: 世界問題(生体データの規制は法域ごとに刑事責任まで含み、
> EU AI Actは一部用途を全域で禁止する)。
> 要約: (1)用途が適法かを実装前に確認する(禁止用途に当たれば
> コードを書かない) (2)生体テンプレートは復元不能な形で扱い、
> 同意と削除の経路を持つ (3)精度は集団別に測定し、単一しきい値の
> 運用を既定にしない。詳細は本文。

## 事実

顔認識の性能は集団間で均一でない。NISTの顔認識ベンダーテスト(FVRT)
Part 3(2019)は、多くのアルゴリズムで偽陽性率が人種・性別・年齢の
集団間で桁単位に異なることを報告した(西アフリカ系・東アジア系、
女性、高齢者・子供で高い)。単一しきい値の照合はこの差をそのまま
運用差に変える。規制面では、EU AI Act(規則2024/1689)第5条が
インターネットやCCTVからの無差別スクレイピングによる顔認識
データベースの構築・拡張、職場・教育での感情認識、法執行の
公共空間でのリアルタイム遠隔生体識別を禁止している(例外は
厳格な列挙に限る)。米国ではイリノイ州BIPA(2008)が生体識別子の
収集前に書面同意を要求し、違反1件あたり過失$1,000・故意$5,000の
私的訴権を持つ。同種の法律が各州・各国で増えており、GDPRは
個人の一意な識別のための生体データを第9条の特別カテゴリとする。
出典: NIST IR 8280、EU AI Act、Illinois BIPA、GDPR(sourcesに記録)。

## 禁止パターン

- 禁止用途への組み込み(EU AI Act第5条の用途、および法域で禁じられた
  監視用途)。適法性の確認なしに実装を進めること自体を含む。
- 無差別スクレイピングによるデータベース構築(収集元の同意・
  robots/規約の確認なしの顔画像収集)。
- 生体テンプレートの可逆保存(原画像の復元が可能な形での保持・
  ログ出力・第三者提供)。
- 単一しきい値での照合(集団別誤り率を測らずに運用する)。
- 本人同意のない照合(オプトアウト手段なしの継続的な照合・追跡)。
- 削除要求に応じた消去経路の欠如(テンプレート・派生embedding・
  キャッシュのいずれかが残る)。
- 属性推定(年齢・性別・感情・民族)を識別と同じ前提で扱うこと
  (推定は誤りやすく、用途によっては別途禁止)。

## 推奨設定

- 用途ゲートをコードに置く: 起動時に用途区分を明示させ、
  禁止区分なら起動を拒否する(設定ミスで本番に載らない形)。
- 集団別の精度評価を必須にする(しきい値ごとにFPR/FNRを
  サブグループ別に出し、運用しきい値を根拠付きで選ぶ)。
- liveness / なりすまし対策を照合パイプラインの一部として設計する
  (提示攻撃・リプレイを前提に).
- 生体テンプレートは不可逆な表現で保存し、保存期間と削除経路を
  設計に含める(原画像は既定で保存しない)。
- 同意記録(取得時の書面同意・目的・期間)をデータと一緒に持つ。
- 監査ログは「いつ・誰が・どのモデル版で照合したか」を残し、
  照合スコアそのものと生体データは残さない。

具体例(用途ゲートと集団別しきい値):

```python
# 用途区分は起動時に明示させ、禁止区分は起動を拒否する
if settings.purpose not in ALLOWED_PURPOSES:  # 設定ミスが本番に載らない形
    raise SystemExit(f"purpose not allowed: {settings.purpose}")

# しきい値は集団別誤り率の表から根拠付きで選ぶ(単一値を既定にしない)
for group, rows in eval_rows.groupby("demographic_group"):
    fpr_by_threshold[group] = false_positive_rates(rows, thresholds)
```

## 運用チェック

- 設定側トリガー(front matter の `triggers.config`)に当たったら、用途区分の確認を促す。
- リリース判定に「用途区分の確認」「集団別評価表の添付」を必須項目と
  して置く。担当: プライバシー/法務のレビュー役。

## 制度変更ウォッチ

- 変更予告: EU AI Actの生体識別関連は段階適用。第5条の禁止は
  2025-02-02から適用済み。高リスク義務(附属書IIIの生体識別等)は当初
  2026-08-02の予定だったが、AI Omnibus(2026-07-27発効)で2027-12-02に
  延期された。確度: 施行済(最終確認: 2026-10-15)。
- 確認TODO: 米国各州の生体情報法の追加(およびBIPA判例の損害額
  算定)を確認する(review_by: 2027-03-31)。
- 影響TODO: 運用中のしきい値を集団別誤り率の観点で再評価し、
  しきい値変更の根拠を記録する。

<!-- 法的助言ではない。専門家レビュー必須。 / This is not legal advice; expert review required. -->

<!-- © kanon contributors (https://github.com/politeuma/kanon). Section domain-face-recognition, licensed CC BY 4.0: https://creativecommons.org/licenses/by/4.0/ -->
