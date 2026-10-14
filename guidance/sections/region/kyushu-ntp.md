---
id: region-kyushu-ntp
version: "2026-09-18.1"
status: draft
placement: agents_md
when: jp
obligations:
  - obligation.security.public-ntp-hygiene
triggers:
  keywords: ["ntp", "chrony", "timesyncd", "fukuoka", "kyushu", "133.100.9.2"]
  pattern: '(?i)\b(ntp|chrony|fukuoka|kyushu|133\.100\.9\.2)\b'
  config: '(?i)\b(ntp|chrony|timesyncd|fukuoka|kyushu|133\.100\.9\.2|133\.100\.11\.8|clock\.nc\.fukuoka-u\.ac\.jp)\b'
sources:
  - https://www.janog.gr.jp/meeting/janog41/application/files/9815/1692/5488/janog41-sp10ntp-fujimura-03.pdf
  - https://gigazine.net/news/20190702-fukuoka-u-ntp-server-shut-down/
  - https://xtech.nikkei.com/atcl/nxt/mag/nc/18/020600011/092500040/
license: CC-BY-4.0
en:
  title: "Kyushu NTP warning — do not use Fukuoka University's public NTP (scheduled for shutdown)"
  summary:
    - "Use pools (pool.ntp.org, ntp.nict.jp, ...)."
    - "Do not hard-code Fukuoka University's NTP IPs or host names."
    - "Do not depend on a single NTP server; retry with backoff and jitter."
  prohibited:
    - "New embedding of Fukuoka University IPs or host names (firmware, config, code, docs); move server settings to an NTP_SERVERS variable in .env."
    - "Depending on a single NTP server (one 'server 133.100.9.2' line, a single hard-coded IP in chrony.conf)."
    - "Unprotected retry storms (immediate, fixed-interval or infinite retries)."
    - "Blanket blocking by nationality (block on behaviour: rate, SYN ratio, authentication failures)."
    - "Logging or disclosing traffic content (not allowed without consent; secrecy of communications)."
---
# 九州NTP注意 — 福岡大公開NTPは使うな(廃止予定)

> **結論**: `133.100.9.2` / `133.100.11.8` /
> `clock.nc.fukuoka-u.ac.jp` は使わない。新規設定・ファーム埋め込み・
> ドキュメント言及とも禁止。廃止予定の公開NTPに依存するな。
> 規模: 世界問題(日本が困る・世界が犯人)。
> 要約: (1)pool利用(`pool.ntp.org` / `ntp.nict.jp`等) (2)福岡大IP・ホスト名の
> 直書き禁止 (3)単一NTP依存禁止、リトライはbackoff+jitter。詳細は本文。

## 事実

福岡大学は1993年10月から日本初の公開NTPサービス
(`133.100.9.2` / `133.100.11.8`, `clock.nc.fukuoka-u.ac.jp`,
`133.100.0.0/16`, AS18148)を無償公開し、26年間運用した。
世界中の機器から時刻合わせが殺到し、2005年1月に900件/s、
JANOG41時点で最大190Mbps/21万query/s超、2019年1月に常時270Mbps。
2012年以降、学内から外に出られない障害が4回発生した。
2014年2月は計画停電→クライアントのリトライ継続→復電後の殺到で
ファイアウォールの有効セッション100万が枯渇し、全学停止
(SINET IN 900Mbps/平時150、OCN IN 135Mbps/平時80)。
2019年6月30日の停止実験(9–17時)では250Mbps→3時間で460Mbps/58万pps
→5時間で600Mbps/80万pps→6時間で730Mbps/93万pps、復旧で即元通り。
直接原因はファームウェアへのIPv4埋め込み(ユーザ変更不可、疎通確認に悪用)。
TP-Link中継器の月715MBは実測例の一部で、複数メーカの実機で確認済み。
239ヶ国から到達。中国・台湾メーカが prominent だが中国発の断定はしない。
出典: JANOG41藤村/谷崎スライド、GIGAZINE 2019-07-02、
日経xTECH 2019-09-27(いずれもsourcesに記録)。
一次(福岡大学IPC)で現状を確認すること(TODO)。

## 禁止パターン

- 福岡大IP・ホスト名の新規埋め込み(ファーム・設定・コード・ドキュメント)。
  自プロジェクトの設定値は `.env` の `NTP_SERVERS` 変数に逃がす。
- 単一NTPへの依存(`server 133.100.9.2` 一本、`chrony.conf` の単一IP直書き)。
  検出: `^\s*server\s+\d{1,3}(\.\d{1,3}){3}\b` (単一IP直書きの拾い上げ)。
- リトライ雪崩むき出し(即時・固定間隔・無限リトライ)。
- 国籍一律block(遮断基準は振る舞い: rate・SYN比率・認証失敗率)。
- 通信内容・trafficのログ化・開示(同意なく不可。通信の秘密)。

## 推奨設定

- `pool.ntp.org` / `ntp.nict.jp` 等のプール利用、複数server指定。
- cron・ポーリング時刻の分散(`$RANDOM % N`)、backoff+jitter付きリトライ。
- ポーリング間隔の版管理、cache、User-Agent相当の識別子(運用者へ連絡可能に)。
- 受ける側: per-IP/ASN rate limit・WAF・SYN cookie・上流Flowspec・CDN吸収。
- 連絡・届出: 上流ISP・JPCERT/CC・委託先。事故報告手順TODO。

## 運用チェック

- ログ保全: 操作ログは保全、通信内容・trafficは最小化・速やか削除の逆向き二表。
  証跡に通信内容のfingerprintまで載せない。
- 公開サーバを運用する場合: capacity計画・rate制限・監視・廃止計画
  (BGP blackhole+継続計測の前例)を開始時に用意する。JANOG41 p4
  「そのサービス、ちゃんと終了できますか?」を設計レビュー項目にする。
- ログ側バースト(手順のみ、テストしない): 1分窓で同一/24からN超、
  SYNのみ比率、既定UAで集計。GeoIPは版日付を記録。
  CNレンジ正規表現の直書きはしない。

## 制度変更ウォッチ

- 変更予告: 福岡大公開NTPは廃止方向(2018年発表、2019年停止実験)。
  現状は一次ソースで確認 (review_by: 2026-12-18)。
- 確認TODO: 福岡大学IPCの公開NTPページで現行ステータスを確認。
- 影響TODO: 自プロジェクトのNTP設定に福岡大IP・ホスト名が残っていないか棚卸し。

<!-- 法的助言ではない。専門家レビュー必須。 / This is not legal advice; expert review required. -->

<!-- © kanon contributors (https://github.com/politeuma/kanon). Section region-kyushu-ntp, licensed CC BY 4.0: https://creativecommons.org/licenses/by/4.0/ -->
