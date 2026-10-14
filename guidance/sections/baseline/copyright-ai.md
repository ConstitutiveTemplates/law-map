---
id: baseline-copyright-ai
version: "2026-09-21.2"
status: active
placement: agents_md
when: [cli, data_science]
obligations:
  - obligation.copyright.ai-training-data-use
triggers:
  keywords: ["scraping", "robots.txt", "rag", "fine-tuning", "dataset", "public-domain"]
  pattern: '(?i)\b(scrap|crawl|robots\.txt|rag|retrieval|fine-?tun|dataset|embedding|public[- ]domain|copyright)\b'
  config: '(?i)\b(robots|scrapy|BeautifulSoup|httpx|rag|chromadb|faiss|langchain)\b'
sources:
  - https://www.bunka.go.jp/seisaku/chosakuken/aiandcopyright.html
license: CC-BY-4.0
en:
  title: "AI and copyright — scraping, training and RAG code must keep the non-enjoyment purpose intact"
  summary:
    - "Do not bypass robots.txt or other access-refusal measures."
    - "Do not design RAG that retrieves and re-emits the protected expression itself; extract facts and concepts."
    - "Do not overfit or fine-tune on a specific body of works in order to imitate it."
  prohibited:
    - "Bypassing access-refusal measures (ROBOTSTXT_OBEY=False, spoofed User-Agent, IP rotation to evade rate limits)."
    - "Fine-tuning or one-shot prompts built to reproduce a specific author's style or a specific repository's implementation."
    - "RAG that returns raw chunks of original expression (consecutive code lines, prose paragraphs) instead of summaries or embeddings."
    - "Feeding scraped data into training or RAG without recording its provenance."
    - "Assuming 'public domain' without checking jurisdiction and term of protection."
---
# AIと著作権 — 取得・学習・RAGコードは「非享受目的」を壊さない

> **適用条件**: ウェブ取得(スクレイピング)、データセット構築、
> fine-tuning、RAG/検索、生成物の再配布を実装する場面。
> 日本法(著作権法30条の4)を軸に、法域差の注意も併記する。
> 規模: 国内問題(30条の4は日本法で、権利者の利益も国内法がまず守る)。
> 要約: (1)robots.txt等の取得拒否措置を回避しない (2)表現そのものを
> 検索・再出力するRAG設計をしない(事実・概念の要約抽出にとどめる)
> (3)模倣を目的とする過学習・特定作品群の追加学習をしない。
> 詳細は本文。

## 事実

文化庁は2024-03、著作権審議会の議論を経て「AIと著作権に関する
考え方について」を公表した。情報解析を目的とする著作物の利用は
著作権法30条の4で原則適法だが、「著作権者の利益を不当に害する場合」は
権利制限の対象外とされる。同考え方は、(1)特定の表現を忠実に再現させる
目的の過学習や特定作品群のみの追加学習は「表現の享受」目的と評価され
30条の4が適用されない、(2)RAGでデータベース内の創作的表現そのものを
検索・取得して出力に含める設計は享受目的の併存が問題になり得る、
(3)robots.txt等の取得拒否措置の意図的な回避は、将来的な有償の
データ解析市場を不当に害し得る、と整理した。生成物の侵害判断は
従来法理と同じく「類似性」と「依拠性」で行われ、学習データ内に
元作品があり生成結果に創作的特徴が感得できれば依拠性が推認され得る。
また保護期間は法域差(死後70年原則、戦時加算、映画・企業名義の扱い)が
あり、パブリックドメイン判定は対象法域ごとの照合が要る。
出典: 文化庁「AIと著作権に関する考え方について」(sourcesに記録)。

## 禁止パターン

- 取得拒否措置の回避(`ROBOTSTXT_OBEY=False`、UA偽装、
  レート制限回避のためのIPローテーション等)。
- 特定作家・特定リポジトリの文体/実装を再現させるfine-tuning・
  ワンショット模倣プロンプト。
- RAGで原文の表現(コードの連続行、文章段落)をそのまま検索・出力する設計
  (要約・埋め込み化でなく生チャンクを返す構成)。
- 出典を記録せずに取得データを学習/RAG基盤へ流す。
- 「パブリックドメイン」の無検証前提(法域・保護期間の照合なし利用)。

## 推奨設定

- 保持は事実・概念レベルに(要約、埋め込み、統計)。生表現の保持は
  ライセンス/利用規約の確認を通したものに限定し、出典を版管理する。
- 出力側に重複検出を入れる(既知ソースとの長い共通n-gramで
  差し戻すフィルタ)。
- 取り込み工程に利用規約・ライセンス確認ステップを置き、
  拒否措置(robots.txt/ToS)の有無をデータセットのメタデータに記録する。
- パブリックドメイン判定は法域+著作者の没年/公表年を入力にする
  チェッカーを通し、判定根拠を残す。法域別の保護期間データ
  (死後年数・団体名義・戦時加算など)は本コーパスの
  `lang/copyright-terms.yml` に構造化してある。本節には要約のみを載せ、
  チェッカー実装時は対象法域の現行法で再確認する。

具体例(取得とRAGの既定形。悪い形と良い形の対):

```python
# 取得は拒否措置を尊重する(標準庫の robots.txt パーサ)
rp = robotparser.RobotFileParser()
rp.set_url(base_url + "/robots.txt")
rp.read()
if not rp.can_fetch(USER_AGENT, url):
    skip(url)  # 迂回(UA 偽装・IP ローテーション)を書かない

# RAG は生チャンクを返さない: 既知ソースとの長い共通 n-gram を差し戻す
if longest_common_ngram(answer, source, n=12):
    reject("output is too close to the source")
```

## 運用チェック

- 取得コードのレビュー項目に「拒否措置の尊重/レート/UAの正直さ」を置く。
  担当: データ取得を実装するレビュー役。

## 制度変更ウォッチ

- 変更予告: 文化庁はAIと著作権の論点の継続的な整理を続けており、
  追加の考え方・論点整理が出る可能性。確度: 審議中。
- 確認TODO: 文化庁ページで最新の考え方・Q&Aを一次で確認
  (review_by: 2027-03-31)。
- 影響TODO: 自プロジェクトの学習/RAGデータの取得元一覧に対し、
  拒否措置の現状を再確認する。

<!-- 法的助言ではない。専門家レビュー必須。 / This is not legal advice; expert review required. -->

<!-- © kanon contributors (https://github.com/politeuma/kanon). Section baseline-copyright-ai, licensed CC BY 4.0: https://creativecommons.org/licenses/by/4.0/ -->
