---
id: baseline-pki-chain
version: "2026-09-21.2"
status: active
placement: agents_md
when: [embedded, cli, web_api]
obligations:
  - obligation.crypto.no-deprecated-algorithms
triggers:
  keywords: ["tls", "cert", "trust-store", "pinning", "mtls", "ca_bundle"]
  pattern: '(?i)\b(certificat|trust\s?store|ca_bundle|pinn|openssl|requests|httpx|urllib3|mtls|root\s?ca|intermediate)\b'
  config: '(?i)\b(chain\.pem|ca_bundle|CERT_NONE|verify\s*=\s*False|pin_sha256)\b'
sources:
  - https://letsencrypt.org/certificates/
  - https://letsencrypt.org/2023/07/10/cross-sign-expiration
  - https://letsencrypt.org/2024/04/12/changes-to-issuance-chains
  - https://community.letsencrypt.org/t/isrg-root-x2-cross-signed-by-isrg-root-x1/239124
  - https://community.cloudflare.com/t/clarification-about-email-upcoming-lets-encrypt-certificate-chain-change/628713
license: CC-BY-4.0
en:
  title: "PKI chain changes — do not hard-code intermediate certificates or issuance chains"
  summary:
    - "Do not bundle or pin intermediate certificates or issuance chains."
    - "Verify against the OS/system trust store and keep a way to update it."
    - "If you pin, pin a set of public keys with a backup key, never a single key."
  prohibited:
    - "Bundling intermediate certificates in the repository or burning them into firmware (a fixed chain.pem)."
    - "Pinning a single intermediate certificate or SPKI with no backup key."
    - "Freezing a private trust store that cannot pick up system updates."
    - "Suppressing verification (verify=False, ssl.CERT_NONE) to work around failures."
    - "Branching on issuer names or chain layout (issuer CN == \"R3\", ...)."
---
# PKIチェーン再編 — 中間証明書・発行チェーンをハードコードしない

> **適用条件**: TLSクライアントの実装、証明書ピン留め、trust storeの
> 同梱・固定、mTLS、長寿命デバイスのファームに証明書を焼く場面。
> 規模: 世界問題(チェーン切れは全世界のクライアントで同時に起きる)。
> 要約: (1)中間証明書や発行チェーンの同梱・固定をしない
> (2)検証はOS/システムのtrust storeに従い、更新手段を持つ
> (3)pinする場合は公開鍵集合+バックアップ鍵で、単一鍵に結びつけない。
> 詳細は本文。

## 事実

Let's Encryptはクロス署名チェーンの段階的廃止を進めている。
DST Root CA X3によるクロス署名は2024-09-30に失効し、長いチェーン自体も
2024-06-06に提供終了した。2024-04からは中間証明書1枚だけの新しい発行
チェーンに移行している。さらにISRG Root X2をISRG Root X1が署名した
クロス署名証明書は2025-09に失効した。Cloudflareも2024-05-15以降、
クロス署名チェーンからの発行を停止している。発行CAやチェーン構成は
事前告知の上で切り替わる(Let's Encryptはロート鍵儀式も計画発表済み)。
ハードコードされた中間証明書、同梱の古いtrust bundle、特定発行チェーンへ
のピン留めは、この種の切り替えで検証失敗(通信障害)になる。
出典: Let's Encrypt公式(chains/ブログ)、コミュニティスレッド、
Cloudflareコミュニティ(sourcesに記録)。

## 禁止パターン

- 中間証明書のリポジトリ同梱・ファーム焼き込み(`chain.pem`の固定同梱)。
- 特定の中間証明書・SPKI単体へのピン留め(バックアップ鍵なし)。
- 独自trust storeの固定(システム更新を取り込めない形)。
- 検証の握りつぶし(`verify=False`, `ssl.CERT_NONE`での障害回避)。
- 発行CA名・チェーン構成を前提にした分岐(`issuer CN == "R3"`等)。

## 推奨設定

- 検証はOS/システムのtrust storeを使い、`certifi`等は依存更新で追う。
  長寿命デバイスはOTA/設定更新でtrust storeを更新できる経路を持つ。
- ピン留めが必要な場合は公開鍵の集合(現行+バックアップ)に対して行い、
  鍵ローテーション手順と失効時の緊急解除を文書化する。
- チェーン検証をCIに入れる(`openssl s_client -showcerts`相当で
  実チェーンを確認し、issuer前提コードを検出する)。
- 有効期限・失効情報(OCSP/CRL・CTログ)の監視を証明書運用の一部にする。

具体例(TLSクライアントの既定形。悪い形と良い形の対):

```python
# 悪い: 検証の握りつぶしと、焼き込み・単一鍵への固定
httpx.get(url, verify=False)  # CERT_NONE での障害回避
requests.get(url, verify="packaging/chain.pem")  # 同梱チェーンの固定
if issuer_cn(cert) == "R3":
    ...  # 発行チェーン前提の分岐

# 良い: 既定の trust store に従い、pin は公開鍵集合で行う
httpx.get(url)  # システムの検証に従う
pin_set = {"sha256/現行の鍵", "sha256/バックアップ鍵"}  # 手順と一緒に版管理
```

## 運用チェック

- 自プロジェクトが同梱する証明書・ピン留め一覧を棚卸しし、
  「発行チェーン切り替えで壊れるか」を質問できる状態にする。
  担当: リリース管理者。

## 制度変更ウォッチ

- 変更予告: Let's Encryptは新しいルート証明書の鍵儀式を計画中。
  確度: 公式告知あり(実施時期は未定)。発行チェーンは今後も変更があり得る。
- 確認TODO: letsencrypt.org/certificates/ で現行チェーン構成を確認
  (review_by: 2026-12-18)。
- 影響TODO: 同梱chain/pinを持つリリース物がある場合、
  チェーン変更告知を監視対象に追加する。

<!-- 法的助言ではない。専門家レビュー必須。 / This is not legal advice; expert review required. -->

<!-- © kanon contributors (https://github.com/politeuma/kanon). Section baseline-pki-chain, licensed CC BY 4.0: https://creativecommons.org/licenses/by/4.0/ -->
