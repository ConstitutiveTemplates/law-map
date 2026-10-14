---
id: domain-prompt-injection
version: "2026-10-06.1"
status: draft
placement: agents_md
when: mcp
obligations:
  - obligation.security.prompt-injection-defense
triggers:
  keywords: ["prompt injection", "jailbreak", "indirect injection", "agent hijacking", "system prompt"]
  pattern: '(?i)\b(prompt[- ]?injection|jailbreak|indirect[- ]?injection|agent[- ]?hijack|system[- ]?prompt|tool[_-]?poisoning)\b'
  config: '(?i)\b(prompt|llm|agent|mcp|rag|system[_-]?prompt)\b'
sources:
  - https://genai.owasp.org/llm-top-10
  - https://arxiv.org/abs/2406.13352
  - https://www.nist.gov/news-events/news/2025/01/technical-blog-strengthening-ai-agent-hijacking-evaluations
license: CC-BY-4.0
en:
  title: "Prompt injection — never execute external input as instructions"
  summary:
    - "Separate instructions from data; never execute external input as instructions."
    - "Restrict agent permissions to a minimal allowlist."
    - "Default to human approval for destructive or outbound operations."
  prohibited:
    - "Concatenating external text (web pages, email bodies, files, DB rows, tool output) into system prompts or instruction fields without delimiters or labels."
    - "Passing externally sourced commands ('follow the instructions on this page') straight to downstream tool calls without validation or an allowlist."
    - "Giving agents broad powers (delete everything, send externally, pay, deploy) without confirmation."
    - "Putting secrets (tokens, keys, personal data) in the same context as external input without separation."
    - "Relying solely on 'the prompt says do not obey' (instruction-level deterrence is demonstrably bypassable)."
---
# プロンプトインジェクション — 外部入力を指示として実行しない

> **適用条件**: LLM API呼び出し・RAG・ツール呼び出し・エージェント
> ループを含むコードを生成・設計する場面。外部テキスト(Web・メール・
> ファイル・DB行・ツール出力)をモデルに入れる設計はすべて対象。
> 規模: 世界問題(攻撃手法と対策基準は国際共通で、実証データも
> 国境を跨ぐ)。
> 要約: (1)指示とデータを分離し、外部入力を指示として実行しない
> (2)エージェントの権限はallowlistの最小限に絞る
> (3)破壊的・送信系の操作は人間承認を既定にする。詳細は本文。

## 事実

OWASP GenAI セキュリティの「Top 10 for LLM Applications」現行版
(2025年版)は LLM01 としてプロンプトインジェクションを筆頭に置く。
直接注入(ユーザ入力に紛れた指示)だけでなく、外部データに埋め込まれた
指示をエージェントが取り込んで実行する**間接注入**(indirect prompt
injection、NIST は agent hijacking とも呼ぶ)がエージェント時代の主戦場に
なっている。NIST の技術ブログ(2025-01)は、データに挿入された悪意ある
指示が AI エージェントに意図しない有害な行動を取らせるとして、
エージェント・ハイジャックの評価強化を呼びかけた。公開ベンチマーク
AgentDojo(Debenedetti et al., 2024)は、現行 LLM が攻撃なしでも
タスクの 66% 未満しか解けない一方、攻撃は現実的なタスク設定で成立する
ことを実証した。漏洩・任意コード実行・不正送信が帰結になりうる。
出典: genai.owasp.org/llm-top-10、arXiv:2406.13352、NIST 技術ブログ。

## 禁止パターン

- 外部テキスト(Web取得文・メール本文・ファイル内容・DB行・ツール出力)を
  システムプロンプトや指示欄にそのまま連結する(区切りも注記もない結合)。
- 「このページの指示に従って」等の外部由来の命令を、そのまま下流の
  ツール呼び出しに渡す(検証・allowlist なしの素通し)。
- エージェントに広い権限(ファイル全削除、外部送信、決済・デプロイ)を
  確認なしで渡す(過剰なエージェンシーの温床)。
- 機密(トークン・鍵・個人情報)を、外部入力と同じコンテキストに
  無区別で載せる(漏洩の材料を攻撃者に渡す)。
- 「プロンプトで『従うな』と書いたから安全」とする対策のみ(指示レベルの
  抑止は迂回の実証がある)。

## 推奨設定

- 指示とデータの分離: 外部入力は引用ブロック・専用フィールドに入れ、
  「以下はデータであり指示ではない」を構造で示す(文字列連結で混ぜない)。
- allowlist の権限設計: ツールは読み取り専用を既定にし、書き込み・送信・
  実行は個別に許可する(`domain-llm-appsec` の最小権限と合わせる)。
- 人間承認ゲート: 破壊的・不可逆・外部送信の操作は必ず承認ステップを
  挟む(自動承認は既定にしない)。
- 出力の構造化検証: LLM 出力はスキーマ検証してから実行し、shell・SQL・
  eval への直渡しをしない。
- 機密の分離: トークン・鍵はツール引数に載せず、環境・保管庫から
  実行時に取る(プロンプトに書かない)。

具体例(外部入力の隔離と承認ゲート):

```python
# 外部テキストは data 欄に隔離し、指示欄には入れない
messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {
        "role": "user",
        "content": [
            {"type": "text", "text": user_request},
            {"type": "data", "text": fetched_page},
        ],
    },
]

# 破壊的・送信系は承認なしに実行しない
if action.is_destructive or action.sends_outward:
    require_human_approval(action.describe())  # 承認なしは実行しない
execute(action)
```

## 運用チェック

- 設定側トリガー(front matter の `triggers.config`)に当たったら、外部入力の扱いを確認する。
- レビュー項目に「外部入力→指示の経路」を必須化する(結合箇所の列挙)。
  担当: セキュリティレビュー役。

## 制度変更ウォッチ

- 変更予告: OWASP Top 10 for LLM Applications の次版(2026)は実証
  インシデントデータに基づく評価への転換が議論中。確度: 審議中。
- 確認TODO: OWASP LLM Top 10 の版更新と AgentDojo の後継ベンチマーク動向を
  一次ソースで確認 (review_by: 2027-03-31)
- 影響TODO: 版更新で番号・名称が動いた場合、本節の参照を名称ベースに
  維持する(番号のみの参照にしない)。

<!-- 法域・業法に触れる節は下の定型免責を残す。法的助言ではない。
     専門家レビュー必須。 / This is not legal advice; expert review required. -->

<!-- © kanon contributors (https://github.com/politeuma/kanon). Section domain-prompt-injection, licensed CC BY 4.0: https://creativecommons.org/licenses/by/4.0/ -->
