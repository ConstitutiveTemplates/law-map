---
id: domain-llm-appsec
version: "2026-09-18.1"
status: active
placement: agents_md
when: mcp
obligations:
  - obligation.ai.llm-appsec-baseline
triggers:
  keywords: ["llm", "prompt", "agent", "mcp", "tool-call", "openai"]
  pattern: '(?i)\b(llm|prompt|agent|tool[_-]?call|mcp|openai|anthropic|chat|completion|system[_-]?prompt|guardrail)\b'
  config: '(?i)\b(shell\s*=\s*True|eval\(|subprocess|tool_choice|mcp|autonomous)\b'
sources:
  - https://genai.owasp.org/llm-top-10/
license: CC-BY-4.0
en:
  title: "LLM apps / MCP security — least privilege, human approval and output validation by default"
  summary:
    - "Restrict tool permissions to an allowlist of the minimum CRUD needed."
    - "Always insert a human approval step before destructive or irreversible operations."
    - "Validate LLM output structurally before acting on it; never pass it straight to a shell."
  prohibited:
    - "Executing LLM output directly (shell=True, eval, string-concatenated SQL)."
    - "Auto-approving destructive or irreversible operations (delete, payment, sending, production deploy)."
    - "Issuing write-scoped tokens where read-only would do."
    - "Embedding secrets (API keys, personal data) in prompts."
    - "Putting full guardrail text or internal schemas in the system prompt (a bypass guide if leaked)."
    - "Unbounded tool loops or API spend (no count or cost limit)."
---
# LLMアプリ/MCP安全設計 — 最小権限・人間承認・出力検証を既定にする

> **適用条件**: LLM API呼び出し、ツール呼び出し、MCPサーバ/クライアント、
> エージェントループを含むコードを生成・設計する場面。
> 規模: 世界問題(OWASP基準は国際共通で、実インシデントも国境を跨ぐ)。
> 要約: (1)ツール権限はallowlistの最小CRUDに絞る (2)破壊的・不可逆な
> 操作の前に必ず人間承認ステップを入れる (3)LLM出力は構造化検証してから
> 実行し、shell直渡しをしない。詳細は本文。

## 事実

OWASP GenAI Security Projectの「Top 10 for LLM Applications」現行版は
2025年版(genai.owasp.org、2024-11公表)で、LLM01 プロンプトインジェクション、
LLM02 機密情報漏洩、LLM03 サプライチェーン、LLM04 データ/モデルポイズニング、
LLM05 不適切な出力ハンドリング、LLM06 過剰なエージェンシー(Excessive
Agency)、LLM07 システムプロンプト漏洩、LLM08 ベクトル/埋め込みの弱点、
LLM09 誤情報(Misinformation)、LLM10 無制限消費、である。番号は版ごとに
動く(2023-24版では過剰エージェンシーは別番号)ため、参照は番号でなく
名称で行う。過剰なエージェンシーは実インシデント(意図しないデータ削除、
不正送金、未承認の送信)として報告されており、モデルに確認なしで
実行権を渡した設計が直接原因になる。誤情報は「流暢で自信のある誤り」
として下流の意思決定を誘導するため、出力を検証なしで動作に使わない。
次版(2026)は実証インシデントデータに基づく評価への転換が議論されている。
出典: genai.owasp.org/llm-top-10 (sourcesに記録。次版は未公表・要確認)。

## 禁止パターン

- LLM出力の直接実行(`shell=True`、`eval`、SQLの文字列連結)。
- 破壊的・不可逆な操作(delete、送金、送信、本番deploy)の自動承認
  (auto-approve、確認ダイアレスの実行)。
- 書き込み権限トークンの無条件発行(read-onlyで足りる場面にwrite権限)。
- 秘密情報(APIキー、個人情報)のプロンプト埋め込み。
- ガードレール・内部schemaの全文をsystem promptに載せる(漏洩時の
  回避手引きになる)。
- 無制限のツールループ・無制限のAPI消費(回数/金額上限なし)。

## 推奨設定

- ツール権限はallowlist(verb × resourceの最小CRUD)。MCPのツールには
  read-only/副作用の有無をアノテーションで明示する。
- 承認ゲートの既定形: LLMが「操作案+差分」を提示 → 人間が確認 →
  実行。実行結果は監査ログに残す。
  ```
  plan = agent.propose(task)          # 構造化出力(schema検証)
  diff = preview(plan)                 # 実行せず影響を提示
  if not human_approves(diff):         # 破壊的操作は必ず人間
      abort(plan)
  result = executor.run(plan, scope=READ_ONLY_UNLESS_APPROVED)
  ```
- 出力はJSON schema等で構造化検証し、検証失敗は実行せず差し戻す。
- 回数・予算・タイムアウトの上限をツールループに設ける。
- 秘密情報はプロンプトに入れず、実行環境側に注入して参照させる。

## 運用チェック

- エージェントコードのレビュー項目: 「最大何が壊せるか」を一問し、
  その答えが人間承認を経ないと起きないことを確認。担当: コードレビュー役。

## 制度変更ウォッチ

- 変更予告: OWASP次版(2026)は実証インシデントデータ基準への転換が
  議論されている。確度: 未確認(2026-09時点で公開ページは2025年版が現行)。
- 確認TODO: genai.owasp.orgで次版の公表と評価方法を確認
  (review_by: 2026-12-18)。
- 影響TODO: 自プロジェクトのMCP/ツール設計を次版の項目名で
  再マッピングできるよう、参照は名称ベースで書く。

<!-- 法的助言ではない。専門家レビュー必須。 / This is not legal advice; expert review required. -->

<!-- © kanon contributors (https://github.com/politeuma/kanon). Section domain-llm-appsec, licensed CC BY 4.0: https://creativecommons.org/licenses/by/4.0/ -->
