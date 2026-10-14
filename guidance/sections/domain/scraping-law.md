---
id: domain-scraping-law
version: "2026-09-24.1"
status: active
placement: agents_md
when: scraping
obligations:
  - obligation.copyright.ai-training-data-use
triggers:
  keywords: ["sitemap", "robotparser", "allowed_domains", "user-agent", "sui generis", "database right", "cfaa", "breach-of-contract"]
  pattern: '(?i)\b(sitemap|robotparser|allowed_domains|user-agent|sui generis|database right|cfaa|breach-of-contract)\b'
  config: '(?i)\b(sitemap|robotparser|allowed_domains|user-agent|sui generis|database right|cfaa|breach-of-contract)\b'
sources:
  - https://cdn.ca9.uscourts.gov/datastore/opinions/2022/04/18/17-16783.pdf
  - https://eur-lex.europa.eu/eli/dir/1996/9/oj
  - https://www.bunka.go.jp/seisaku/chosakuken/aiandcopyright.html
  - https://laws.e-gov.go.jp/law/411AC0000000128
  - https://www.rfc-editor.org/rfc/rfc9309.html
  - https://eur-lex.europa.eu/eli/reg/2016/679/oj
  - https://www.ppc.go.jp/personalinfo/legal/
license: CC-BY-4.0
en:
  title: "Scraping legality — check rights, contracts and personal data before fetching"
  summary:
    - "Settle whether you may fetch from each site's terms and robots.txt first."
    - "Even for public data, extracting a substantial part of a database or redistributing expression can infringe other rights."
    - "Personal data is regulated both when fetched and when processed."
  prohibited:
    - "Circumventing access control (bypassing login, continuing after being blocked, IP rotation to evade rate limits or bans, generating CAPTCHA solvers); this is unauthorised access, not scraping."
    - "Ignoring robots.txt refusals (ROBOTSTXT_OBEY=False, spoofed User-Agent, direct access to disallowed paths)."
    - "Extracting and reusing substantial parts (catalogues, directories, price data that may carry the EU database right) without assessment."
    - "Redistributing on the assumption public means free (republishing fetched text, images or code without a rights check)."
    - "Fetching and storing personal data with no legal basis, purpose or deletion path."
    - "Justifying worldwide use from one jurisdiction (treating 'fine under the US CFAA' as 'fine under EU database right and the GDPR')."
---
# スクレイピングの適法性 — 取得の前に権利・契約・個人情報を確認する

> **適用条件**: 第三者のウェブページやAPIからデータを取得するコード
> (fetcher / spider / crawler / browser_fetch)を書く・走らせる場面。
> 対象サイトの利用規約、robots.txt、著作権・データベース権、個人情報の
> 有無を確かめないまま取得を始めようとしているなら、本節を先に読む。
> 規模: 世界問題(取得の適法性は法域ごとに分立し、EU・米国・日本の
> いずれの法も関係し得る)。
> 要約: (1)取得の可否はサイトごとの契約とrobots.txtで先に確定する
> (2)公開データでも、データベースの実質部分の抽出や表現の再配布は
> 別の権利を侵害し得る (3)個人情報は取得も処理も規制の対象になる。
> 詳細は本文。

## 事実

スクレイピングは「違法か適法か」の二択ではなく、複数の層の重なりで
判断される。

- **著作権**: ページの表現(文章・画像・コード)は著作権の対象で、
  取得それ自体より再配布・公衆送信が問題になる。日本法では情報解析を
  目的とする利用(著作権法30条の4)に一定の余地があるが、「著作権者の
  利益を不当に害する場合」は対象外で、robots.txt等の取得拒否措置の
  意図的な回避は有償のデータ解析市場を害し得るとされる(文化庁
  「AIと著作権に関する考え方について」、本テンプレートの
  `baseline-copyright-ai` 節が詳説)。
- **データベース権**: EUデータベース指令(96/9/EC)第7条は、内容の取得・
  検証・提示に実質的投資をしたデータベースについて、その実質部分の
  「抽出・再利用」を禁じる独自の権利(sui generis right)を認める。
  個々の事実が著作物でなくても、実質部分の体系的・反復的な抽出は
  侵害になり得る。
- **契約(利用規約)**: サイトのToSは契約であり、公開ページの閲覧が
  技術的に可能でも、ToS違反は契約違反・不法行為として訴えられ得る。
  米国第9巡回区控訴裁判所のhiQ Labs v. LinkedIn(2022)は、公開データに
  ついてはCFAAの「無権限アクセス」に当たらないとの解釈を示したが、
  契約違反や営業秘密・不法行為の請求まで否定したものではない。
- **不正アクセス**: CFAA(18 U.S.C. §1030)や不正アクセス禁止法は、
  認証を回避して保護された計算機に侵入する行為を罰する。公開ページの
  閲覧は原則その対象外だが、ログイン後のアカウント停止後に
  アクセスを続ける、他人の認証情報を使う、技術的保護を回避する、
  といった行為はここに踏み込む。
- **個人情報**: スクレイピングで得た個人情報も、GDPR・個人情報保護法
  (APPI)・米国各州法の適用を受ける。取得の適法根拠、利用目的の特定、
  本人の権利(削除・訂正)、越境移転の管理が必要になる(詳細は
  `baseline-personal-data` 節)。
- **robots.txt**: RFC 9309 が Robots Exclusion Protocol を標準化する。
  robots.txt は運用者がクローラに表明する意思であり、従うことは
  適法性を保証せず、無視することは悪意の証拠になり得る。許可は
  せいぜい「契約違反の抗弁を弱める」材料で、法的な許可証ではない。

出典: hiQ Labs v. LinkedIn(9th Cir. 2022)、EU指令96/9/EC、文化庁
「AIと著作権に関する考え方について」、不正アクセス禁止法、RFC 9309、
GDPR、個人情報保護法(sourcesに記録)。

## 禁止パターン

- アクセス制御の回避(ログイン必須ページへの認証回避、停止後の
  アクセス継続、レート制限・BANのIPローテーション等での回避、
  CAPTCHAソルバの生成)。これはスクレイピングではなく不正アクセスに
  なる。
- robots.txt の拒否の無視(`ROBOTSTXT_OBEY=False`、UA偽装、
  拒否パスへの直アクセス)。
- 実質部分の抽出・再利用(EUデータベース権の対象になり得る
  カタログ・ディレクトリ・価格情報等を、判断なく丸ごと取り込む)。
- 公開＝自由とみなした再配布(取得した表現・画像・コードを、
  権利確認なしにそのまま公開・再配布する)。
- 個人情報の無根拠な取得・保存(適法根拠、利用目的、削除経路を
  持たないまま蓄積する)。
- 単一法域の判断で全世界を正当化する(米国CFAAで問題ないことを、
  EUのデータベース権・GDPRで問題ないことと同一視する)。

## 推奨設定

- 取得元ごとに法的判断を台帳化し、判断のない取得をコードで拒否する。
  台帳には robots.txt の許可、ToS確認の有無、権利区分、確認日を残す。
- 拒否は拒否として扱う(401/403・robots.txt拒否は迂回せず、APIや
  許諾の経路に切り替える)。
- 保持は事実・要約のレベルに留める。実質部分の抽出・再利用は、
  権利確認を通したものに限定し、出典を版管理する。
- 個人情報は最小化し、識別子を抑制し、削除要求に応える経路を
  最初から設計に含める。
- 法域をデータのメタデータとして持つ(EUデータベース権が及び得る
  ソースは「実質部分」を超えない範囲に設計する)。

具体例(取得元ポリシーの台帳と、判断なし取得の拒否):

```python
# 取得元ごとの判断を記録する。記録のない取得は実行しない。
@dataclass
class SourcePolicy:
    base_url: str
    robots_ok: bool  # robots.txt で許可されている(確認時点)
    tos_checked: bool  # 利用規約を確認した(確認時点)
    rights: str  # copyright / database-right / personal-data / none
    checked_on: str  # ISO 日付


def fetch(source: SourcePolicy, url: str) -> bytes:
    if not (source.robots_ok and source.tos_checked):
        raise RuntimeError(f"pre-crawl check missing for {source.base_url}")
    return http_get(url)  # 1 req/s とキャッシュを経由する
```

## 運用チェック

- 設定側トリガー(front matter の `triggers.config`)に当たったら、取得元ポリシーの確認を促す。
- 取得コードのレビュー項目に「取得元ごとの robots/ToS/権利区分の記録」
  を置く。担当: データ取得を実装するレビュー役と、法務・コンプライアンス
  の確認役。

## 制度変更ウォッチ

- 変更予告: hiQ v. LinkedIn の差戻し後の下級審判断、EUのデータベース権
  見直し・AI Actのスクレイピング関連規定、各国のスクレイピング判例は
  動いている。確度: 進行中。
- 確認TODO: 取得元ごとのToS・robots.txtの現状と、EUデータベース権・
  CFAA・不正アクセス禁止法の最新の解釈を一次で確認する
  (review_by: 2027-03-31)。
- 影響TODO: 運用中のクロール対象一覧を見直し、実質部分の抽出や
  個人情報の取り込みがないかを再点検する。

<!-- 法的助言ではない。専門家レビュー必須。 / This is not legal advice; expert review required. -->

<!-- © kanon contributors (https://github.com/politeuma/kanon). Section domain-scraping-law, licensed CC BY 4.0: https://creativecommons.org/licenses/by/4.0/ -->
