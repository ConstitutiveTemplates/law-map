---
id: region-eu-eaa
version: "2026-09-18.1"
status: draft
placement: agents_md
when: eu_market
obligations:
  - obligation.accessibility.european-accessibility-act
triggers:
  keywords: ["accessibility", "wcag", "aria", "a11y", "axe", "keyboard"]
  pattern: '(?i)\b(accessib|aria|wcag|a11y|axe|alt=|tabindex|focus|screen[ -]reader|en[ -]301[ -]549)\b'
  config: '(?i)\b(aria-|role=|tabindex|alt=|wcag|a11y|accessib)\b'
sources:
  - https://eur-lex.europa.eu/eli/dir/2019/882/oj
  - https://www.etsi.org/deliver/etsi_en/301500_301599/301549/
license: CC-BY-4.0
en:
  title: "European Accessibility Act — UIs for the EU are a legal obligation from 2025-06-28"
  summary:
    - "Use EN 301 549 (equivalent to WCAG 2.1 AA) as the technical standard."
    - "Meet keyboard operation, contrast, alt text and labels by default."
    - "Decide exemptions (e.g. microenterprises) with documented grounds."
  prohibited:
    - "Modals or carousels that cannot be operated by keyboard (no focus movement, no Esc to close)."
    - "Insufficient text contrast (below 4.5:1 for body text)."
    - "Images without alt text; form controls without labels."
    - "No focus management on SPA navigation (screen-reader position gets lost)."
    - "Misusing ARIA (hiding real content with aria-hidden, wrong role values)."
    - "Assuming 'not for the EU' without checking whether the service is reachable from within the EU."
---
# 欧州アクセシビリティ法 — 2025-06-28以降のEU向けUIは法定義務

> **適用条件**: EU域内の利用者に提供するECサイト、電子書籍、銀行等の
> 消費者向けサービス、およびそのフロントエンド/UIコンポーネントを
> 実装する場面。
> 規模: 地域問題(EU域内の利用者が被り、域内法が義務づける)。
> 要約: (1)EN 301 549(WCAG 2.1 AA相当)を技術基準にする
> (2)キーボード操作・コントラスト・alt・ラベルを標準で満たす
> (3)microenterprise等の適用除外は根拠付きで判定する。詳細は本文。

## 事実

欧州アクセシビリティ法(EAA、指令(EU) 2019/882)は2025-06-28に適用され、
EU域内で提供されるECサイト、電子書籍、銀行サービス等の消費者向け
サービスとその端末に、障害者・高齢者が支障なく利用できるUIを
法的義務として要求する。技術基準は調和規格EN 301 549
(WCAG 2.1 Level AAの要件を含む)で満たすのが実務上の本体路線。
2025-06-28前に締結済みのサービス契約は最長5年(2030-06-28まで)、
セルフサービス端末は経済耐用年数(上限20年)の猶予がある。適用除外は
小規模事業者(microenterprise: 従業員10人未満かつ売上高200万ユーロ以下
が提供するサービス)などに限定され、当事業が該当するかの判定は
根拠を残して行う。違反には各国市場監視当局による是正・制裁が
課され得る。
出典: 指令(EU) 2019/882(EUR-Lex)、ETSI EN 301 549(sourcesに記録)。

## 禁止パターン

- キーボードで操作できないモーダル・カルーセル(フォーカス移動・
  Esc閉じがない)。
- コントラスト不足のテキスト(4.5:1未満の常用文字)。
- 画像のalt欠如、フォームコントロールのlabel欠如。
- SPA遷移でのフォーカス管理欠如(読み上げ位置が迷子になる)。
- 装飾情報をariaで誤魔化す(`aria-hidden`での本命データ隠し、
  誤ったrole指定)。
- 「EU向けじゃない」の無検証前提(域内から利用可能なら対象になり得る
  という判定をせずに除外)。

## 推奨設定

- CIにaxe-core/Lighthouse相当の自動チェックを置き、
  critical違反をマージブロックにする。
- セマンティックHTML先行(見出し・ランドマーク・ネイティブ要素)で、
  ARIAは補完に使う(ARIAを足して壊さない)。
- フォーカス管理: 遷移時のフォーカス移動、skip link、
  `prefers-reduced-motion`への追従。
- EN 301 549のチェックリストをリリース判定に置き、
  適用除外(該当非該当)の判定記録を残す。

## 運用チェック

- UIの変更レビューに「キーボードだけで操作できるか」を必須項目として
  置く。担当: フロントエンドのレビュー役。

## 制度変更ウォッチ

- 変更予告: 各国の移入法と制裁額・市場監視の運用は国ごとに固められて
  いる。確度: 施行済(移入法の細部は国別に確認)。
- 確認TODO: EN 301 549の現行版と各国移入法の制裁規定を一次で確認
  (review_by: 2027-03-31)。
- 影響TODO: 自プロジェクトのUIコンポーネントに自動a11yチェックを
  組み込み、既存画面の違反を棚卸しする。

<!-- 法的助言ではない。専門家レビュー必須。 / This is not legal advice; expert review required. -->

<!-- © kanon contributors (https://github.com/politeuma/kanon). Section region-eu-eaa, licensed CC BY 4.0: https://creativecommons.org/licenses/by/4.0/ -->
