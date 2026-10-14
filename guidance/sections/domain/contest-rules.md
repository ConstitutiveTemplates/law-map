---
id: domain-contest-rules
version: "2026-09-24.1"
status: active
placement: agents_md
when: oj_code
obligations:
  - obligation.ai.contest-rules-compliance
triggers:
  keywords: ["atcoder", "leetcode", "codeforces", "yukicoder", "kattis", "online-judge"]
  pattern: '(?i)\b(atcoder|leetcode|codeforces|yukicoder|aoj|kattis|competitive-programming|online-judge|kattisrc|oj\s+submit)\b'
  config: '(?i)\b(atcoder|leetcode|codeforces|yukicoder|aoj|kattis|competitive-programming|online-judge|kattisrc|oj\s+submit)\b'
sources:
  - https://info.atcoder.jp/entry/llm-rules-ja
  - https://atcoder.jp/posts/1347
  - https://icpc.global/regionals/rules
  - https://leetcode.com/contest/
  - https://codeforces.com/
  - https://open.kattis.com/
license: CC-BY-4.0
en:
  title: "Contest rules — AI use differs per contest, and the submitter is responsible"
  summary:
    - "Whether AI may be used differs by contest and over time; check the current rules before generating or submitting."
    - "When the rules are unclear, treat AI use as prohibited."
    - "The submitter is responsible; multiple accounts and rating manipulation are banned on every judge."
  prohibited:
    - "Having AI generate solutions in a contest whose rules forbid it (e.g. leaving code completion on during an AtCoder ABC/ARC/AGC)."
    - "Submitting without checking the rules ('it is probably allowed')."
    - "AI use beyond the exceptions the rules allow (AtCoder's translation exception covers translation with the prescribed preamble only, not summaries, solution hints or debugging)."
    - "Multiple accounts, rating manipulation, account sharing or proxy submission."
    - "Leaking problem statements or solutions to third parties during a contest."
---
# コンテスト規約 — AI利用は大会ごとに違い、提出は本人の責任

> **適用条件**: 競技プログラミング・オンラインジャッジの解答コードを
> 書く、または提出する場面(AtCoder / LeetCode / Codeforces /
> yukicoder / AOJ / Kattis / その他のジャッジ)。
> 規模: 世界問題(各ジャッジが独自の規約を制定・改定し、法域としての
> 統一規則は存在しない)。
> 要約: (1)AI利用の可否は大会・時期ごとに異なるので、生成・提出の前に
> 現行規約を確認する (2)規約が不明なときは禁止として扱う
> (3)提出は本人の責任であり、複数アカウント・レーティング操作は
> どのジャッジでも禁止される。詳細は本文。

## 事実

コンテスト中のAI利用ルールは、ジャッジ・大会・時期によって異なる。

- **AtCoder**: 「生成AI対策ルール」(2025-10-03版)は、開催中のABC・ARC・
  AGCで生成AIの使用を原則禁止する。許される例外は問題文の翻訳に限られ、
  対話型AIには所定の前置き文と問題文だけを与えること、翻訳専用AIには
  問題文をそのまま入力することが認められる。問題文の要約、コードや
  解法の生成、コンパイルエラーやバグの診断、AIベースのコード補完
  (Copilot等)の使用は禁止される。コンテスト開始前にAIで作成済みの
  コードの使用は許容され、過去問の練習には適用されない。AHC
  (ヒューリスティック)には別のルールが適用される。
- **他ジャッジ**: LeetCode・Codeforces・Kattis・ICPC などはそれぞれ
  独自の規約を持ち、AI利用の可否・範囲・罰則は一致しない。したがって
  「前回は許された」は根拠にならない。規約は改定され続けている
  (AtCoder は 2024-11 → 2025-10 → 2026-08 と短期間で改定している)。
- **提出は本人の責任**: どのツールで生成したかに関わらず、提出した
  アカウントの持ち主が結果に責任を負う。判定はジャッジが行い、
  ツールやテンプレートが許可を保証することはない。
- **レーティング操作・複数アカウント**: 複数アカウントの所持・使い分け、
  レーティング操作、アカウントの共有、他人への代理提出、開催中の
  問題の漏洩は、どのジャッジでも禁止され、失格・BANの対象になる。

出典: AtCoder「生成AI対策ルール」・関連アナウンス、ICPC Regional Rules、
各ジャッジの規約(sourcesに記録)。

## 禁止パターン

- 規約がAI生成を禁じている大会で、AIに解答コードを生成させる
  (AtCoder ABC/ARC/AGC の開催中、コード補完を切らずに使う等)。
- 規約を確認せずに提出する(「たぶん許される」で生成・提出する)。
- 規約が許す例外を超えたAI利用(AtCoderの翻訳例外は所定の前置き文を
  伴う翻訳のみで、要約・解法説明・デバッグは含まない)。
- 複数アカウントの運用、レーティング操作、アカウント共有、代理提出。
- 開催中の問題文・解答の第三者への漏洩。

## 推奨設定

- 提出前に、そのジャッジの現行規約を確認し、確認したURLと日付を
  問題ごとに残す。規約が不明なときは禁止として扱う。
- 規約がAI利用を禁じる大会では、生成AI・コード補完をオフにし、
  自分で書いた解答のみを提出する。
- 学習・練習(過去問)と本番を区別し、本番の規約を練習時の慣習で
  上書きしない。
- 複数アカウントや代理提出の依頼は、ツールの一部として実装しない。

具体例(規約確認を提出の前提条件にする):

```python
# その大会の現行規約を確認してから生成・提出する(未確認は禁止扱い)
def contest_allows_ai(judge: str, rules_url: str, ai_allowed: bool | None) -> bool:
    if ai_allowed is None:
        raise RuntimeError(f"AI rule unknown for {judge}, {rules_url}")
    return ai_allowed
```

## 運用チェック

- 設定側トリガー(front matter の `triggers.config`)に当たったら、現行規約の確認を促す。
- 提出前チェックの項目に「現行規約の確認(URL・日付)」を置く。
  担当: 提出する本人と、提出物をレビューする役。

## 制度変更ウォッチ

- 変更予告: 生成AIの能力向上に合わせて各ジャッジのルールは頻繁に
  改定される(AtCoderは短期AHCのルールも別途改定)。確度: 進行中。
- 確認TODO: 対象ジャッジの現行規約(AI利用・複数アカウント・
  レーティング操作)を一次ソースで確認する(review_by: 2027-03-31)。
- 影響TODO: AGENTS.md のAI利用に関する文言が、確認した規約と
  食い違っていないかを見直す。

<!-- 法的助言ではない。専門家レビュー必須。 / This is not legal advice; expert review required. -->

<!-- © kanon contributors (https://github.com/politeuma/kanon). Section domain-contest-rules, licensed CC BY 4.0: https://creativecommons.org/licenses/by/4.0/ -->
