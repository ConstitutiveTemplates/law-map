---
id: region-jp-external-transmission
version: "2026-09-18.1"
status: draft
placement: agents_md
when: jp
obligations:
  - obligation.privacy.external-transmission-declared
triggers:
  keywords: ["cookie", "consent", "gtm", "analytics", "optout", "tracking"]
  pattern: '(?i)\b(cookie|consent|gtm|gtag|analytics|opt-?out|tracker|advertis|sdk|tag manager)\b'
  config: '(?i)\b(gtm|gtag|analytics|cookie|consent|tracking)\b'
sources:
  - https://laws.e-gov.go.jp/law/404AC0000000086
license: CC-BY-4.0
en:
  title: "Japan external transmission rules — disclose third-party sends from Japan-facing front ends in advance"
  summary:
    - "Publish in plain Japanese, in advance, what is sent, to which company, and for what purpose."
    - "Keep the disclosure legible (text size, contrast)."
    - "Separate out sends made at the user's request (e.g. authentication) under the exemption, with documented grounds."
  prohibited:
    - "Installing tags wholesale without notice or consent (a tag manager opened up for analytics and ads)."
    - "Illegible disclosure (unreadably small text, low contrast, buried deep on another page)."
    - "Jargon-only explanations ('identifiers are sent' without saying what information)."
    - "Vague recipients only ('advertising partners, etc.' with no company names or link to details)."
    - "No way to opt out (consent screens with no refusal option)."
    - "Claiming the exemption without grounds ('it is an auth cookie, so no disclosure' with nothing recorded)."
---
# 外部送信規律 — 日本向けフロントエンドのサードパーティ送信は事前開示を

> **適用条件**: 日本の利用者を対象にWebサイト・アプリを提供し、
> アクセス解析・広告・サードパーティタグ/SDK・Cookie等で
> 利用者端末から外部へ情報を自動送信させる場面。
> 規模: 国内問題(規制も利用者の被害も日本国内に閉じる)。
> 要約: (1)送信情報・送信先事業者・利用目的を平易な日本語で事前公表
> (2)文字サイズ・コントラスト等の視認性を確保する
> (3)本人の要求に基づく送信(認証等)は適用除外を根拠付きで切り分ける。
> 詳細は本文。

## 事実

改正電気通信事業法(2023-06-16施行)の外部送信規律(第27条の12)は、
利用者の個人情報に該当し得る情報を通信の秘密に触れない形で外部送信する
事業者に、あらかじめその概要を公表・通知することを義務づけた。
総務省のガイドブック・チェックシートは、必須開示項目として
(1)送信される情報の内容 (2)送信先事業者の氏名または名称
(3)自社と送信先における利用目的 を挙げ、平易な表現と
文字サイズ・コントラストに配慮した視認性の高いUIを要求する。
一方で、本人の要求に基づく送信(認証のためのCookie等)で通信の秘密に
触れないものは適用除外として切り分けられる。開示は階層的構成
(一覧+詳細)が認められ、送信先の名称を略称とし詳細への遷移で
足し合わせる形もガイドライン改定で整理されている。
出典: 電気通信事業法(e-Gov法令検索)、総務省ガイドブック
(sourcesに記録。ガイドブック最新版は一次で確認)。

## 禁止パターン

- 通知/同意なしのタグ一括設置(タグマネージャで解析・広告を
  全開放したまま公開)。
- 視認性の欠如(縮小で読めない文字サイズ、背景と同化するコントラスト、
  別画面の深部への押し込み)。
- 専門用語のみの説明(「識別子を送信します」だけで情報内容を説明しない)。
- 送信先の曖昧化のみ(「広告パートナー等」とだけ書き、事業者名・
  詳細への導線を置かない)。
- オプトアウト不能設計(拒否手段がない同意画面)。
- 適用除外の無根拠適用(認証Cookieだから開示不要、と根拠を残さない)。

## 推奨設定

- 送信前ゲート: 同意/設定の状態に応じてタグの発火を制御する
  (タグマネージャの配信トリガーを同意状態に紐づける)。
- 開示の3列表(送信情報/送信先/利用目的)を一覧ページに持ち、
  各行から詳細へ遷移させる。
- 平易な日本語の説明文(「アクセス解析のため、ページを見た記録を
  会社〇〇に送ります」程度の文)を既定の文体にする。
- 視認性: WCAG AA相当のコントラスト(4.5:1)、端末拡縮に依存しない
  文字サイズ。
- 適用除外は「なぜ除外か」を1行で文書化し、プライバシーポリシーに
  反映する。

## 運用チェック

- タグ/SDK追加時のレビュー項目に「開示表の行追加」を置く。
  担当: フロントエンドのレビュー役。

## 制度変更ウォッチ

- 変更予告: 総務省はガイドブック・チェックシートを改定しており、
  開示表記の細部(略称・遷移)が動く。確度: 改定あり(2024年以降)。
- 確認TODO: 総務省の外部送信規律ガイドブック最新版で開示要件を確認
  (review_by: 2027-03-31)。
- 影響TODO: 自プロジェクトのタグ一覧を棚卸しし、開示表の行と
  実装の差分をなくす。

<!-- 法的助言ではない。専門家レビュー必須。 / This is not legal advice; expert review required. -->

<!-- © kanon contributors (https://github.com/politeuma/kanon). Section region-jp-external-transmission, licensed CC BY 4.0: https://creativecommons.org/licenses/by/4.0/ -->
