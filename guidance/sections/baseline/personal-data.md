---
id: baseline-personal-data
version: "2026-10-15.1"
status: active
placement: agents_md
when: [personal_data, face_recognition, medtech]
obligations:
  - obligation.privacy.external-transmission-declared
  - obligation.privacy.no-cleartext-pii-logging
triggers:
  keywords: ["pii", "personal", "gdpr", "privacy", "user_data", "deletion"]
  pattern: '(?i)\b(pii|personal[_ ]?data|personal[_ ]?information|gdpr|privacy|user[_ ]?data|deletion|right[_ ]?to[_ ]?erasure|consent|retention)\b'
  config: '(?i)\b(pii|personal_data|gdpr|privacy|delete_account|right_to_erasure|scrub|redact)\b'
sources:
  - https://eur-lex.europa.eu/eli/reg/2016/679/oj
  - https://www.ppc.go.jp/personalinfo/legal/
  - https://oag.ca.gov/privacy/ccpa
license: CC-BY-4.0
en:
  title: "Personal data — minimise before collecting, and build the deletion path first"
  summary:
    - "Ask whether each item is needed before collecting it; default to the minimum."
    - "Include deletion and correction paths in the initial design; retrofitting is expensive."
    - "Know what leaves the process (error trackers, cloud, external APIs) and reduce it before it leaves."
  prohibited:
    - "Collection without a defined purpose ('we might use it later')."
    - "Logs that keep request bodies, query strings or IPs by default with no retention period."
    - "No real deletion path (logical delete only, or copies left in backups, derived tables, caches, search indexes)."
    - "Sending personal data unconditionally to third parties (error trackers, analytics, LLM APIs)."
    - "Logging passwords, tokens or API keys."
    - "Automated decisions without a record of inputs, model version and output."
    - "Copying production data into development environments without anonymisation."
---
# 個人データ — 集める前に最小化し、消せる経路を先に作る

> **適用条件**: 識別できる人に関するデータ(アカウント、連絡先、注文、
> IPや利用者IDを残すログ、メッセージ、アップロードされたファイル、
> 解析イベント)を、保存・送信・処理する場面。通過するだけの場合も含む。
> 自動的に判断を下す場合(評価・順位付け・承認・審査・照合)も本節の
> 対象で、その場合は人間の関与と説明可能性が加わる。
> 規模: 世界問題(データは国境を越えて流れ、法域ごとに要件が重なる)。
> 要約: (1)集める前に「これは必要か」を問い、既定を最小にする
> (2)削除・訂正の経路を初期設計に含める(後付けは高くつく)
> (3)プロセスを出るもの(Sentry・クラウド・外部API)を把握し、
> 出る前に減らす。詳細は本文。

## 事実

個人データの保護は、法域ごとに**独立した義務**として課される。
EUのGDPR(2016/679、2018-05-25適用)は、個人データを「識別され
または識別され得る自然人に関する情報」と広く定義し(第4条1)、
処理の適法性(第6条)、データ最小化(第5条1c)、保存期間の制限
(第5条1e)、削除権(第17条)、自動化された意思決定に関する権利
(第22条)を定める。違反時の制裁は全世界売上の4%または2,000万ユーロの
いずれか高い方まで及ぶ(第83条5)。日本の個人情報保護法も同種の
義務を課し、2020年改正(2022-04-01施行)で漏えい等報告を義務化した。米国は連邦一般法を
持たず州法の重層(CCPA/CPRA、その他の州法)で、イリノイ州BIPAの
ように生体情報へ独自の同意要件を課す州もある。

技術的な帰結として重要なのは、**これらが「保存しているもの」だけでなく
「通過するもの」にも及ぶ**ことだ。エラートラッカーに送られた
リクエストボディ、クラウドのアクセスログ、LLM APIへ送ったプロンプトは、
いずれも処理に当たる。設計時に把握していない送信経路が、事後に
最大の負債になる。出典: GDPR、個人情報保護法、CCPA/CPRA
(sourcesに記録)。

## 禁止パターン

- 目的を決めない収集(「あとで使うかも」で列を足す)。
- 既定で残るログ(リクエストボディ・クエリ文字列・IPをそのまま記録し、
  保持期間を決めない)。
- 削除経路の欠如(アカウント削除が論理削除のみ、またはバックアップ・
  派生テーブル・キャッシュ・検索インデックスに残る)。
- 第三者への無条件送信(エラートラッカー・解析・LLM APIへ
  個人データをそのまま渡す)。
- パスワード・トークン・APIキーのログ出力。
- 自動化された判断の記録を残さない(何を入力に、どの版が、
  何を返したかが追えない)。
- 本番データの開発環境への複製(匿名化なしのコピー)。

## 推奨設定

- 新しく列を足す前に「この列は何の目的に必要か」を1行書く。書けない
  なら足さない。
- ログは既定で最小化する: リクエストボディとクエリ文字列を落とし、
  識別子は必要なら仮名化して残す。保持期間を設定で持つ。
- 削除を1つの操作にする: `DELETE /resource/{id}` が本体・関連行・
  派生キャッシュまで到達することをテストで固定する。
- 外部送信を列挙する: プロセスから出る宛先をコード上の一覧
  (設定値でもよい)にし、それぞれに「何を送るか」を書く。
  Sentry 等は送信前スクラブ(`before_send`)を既定にする。
- 自動判断は説明可能な形で記録する(入力の要約・モデル版・結果・
  人間の確認有無)。
- 開発環境は本番データを使わない。必要なら生成データで代替する。

具体例(ログとエラートラッカーの最小化。悪い形と良い形の対):

```python
# 悪い: 本文・トークンがそのまま外へ出る
async def log_request_bad(request, user_id, e):
    logger.info("payload", body=await request.body())  # 本文が外へ出る
    capture_exception(e)  # 送信前スクラブなし


# 良い: 落とす列を既定にし、識別子は仮名化する
async def log_request_good(request, user_id):
    payload = await request.json()
    logger.info("request", keys=sorted(payload), user_ref=pseudonym(user_id))
    init_error_tracker(before_send=scrub_pii)  # プロセス外に出る前に削る
```

## 運用チェック

- 設定側トリガー(front matter の `triggers.config`)に当たったら、送信先の列挙と削除経路の有無を確認する。
- リリース判定に「新しい個人データ項目の追加はないか」「新しい
  送信先はないか」を必須項目として置く。担当: データ保護のレビュー役。

## 制度変更ウォッチ

- 変更予告: EU AI Actの高リスク義務は個人データを扱うAIシステムに
  追加の要件を重ねる。当初2026-08-02適用の予定だったが、AI Omnibus
  (2026-07-27発効)で延期され、単体の高リスク(附属書III)は2027-12-02、
  製品組込み型(附属書I)は2028-08-02から適用。
  確度: 施行済(延期後の日程確定、最終確認: 2026-10-15)。
- 確認TODO: 自プロジェクトが展開する法域の州法追加(米国)と、
  越境移転の枠組み(SCC・十分性認定)の変更を確認する
  (review_by: 2027-03-31)。
- 影響TODO: 外部送信の列挙を実際に作り、各行に送信内容と
  スクラブの有無を記入する。

<!-- 法的助言ではない。専門家レビュー必須。 / This is not legal advice; expert review required. -->

<!-- © kanon contributors (https://github.com/politeuma/kanon). Section baseline-personal-data, licensed CC BY 4.0: https://creativecommons.org/licenses/by/4.0/ -->
