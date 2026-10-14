---
id: baseline-deprecated-crypto
version: "2026-10-06.1"
status: draft
placement: agents_md
when: always
obligations:
  - obligation.crypto.no-deprecated-algorithms
triggers:
  keywords: ["md5", "sha1", "sha-1", "des", "3des", "rc4", "sslv3", "tls1.0", "tls1.1", "sha1withrsa"]
  pattern: '(?i)\b(md5|sha-?1(?!6|384|512)|(?<!3)des(?!c)|3des|triple-?des|rc4|sslv?3|tls\s?1\.[01]|sha1withrsa|rsa[_ /-]?1024)\b'
  config: '(?i)\b(md5|sha-?1|des|3des|rc4|sslv3|tls\s?1\.[01]|sha1withrsa)\b'
sources:
  - https://csrc.nist.gov/pubs/sp/800/131/a/r2/final
  - https://www.cryptrec.go.jp/en/index.html
license: CC-BY-4.0
en:
  title: "Deprecated cryptography — no new MD5/SHA-1 signatures, DES family, or TLS 1.0/1.1"
  summary:
    - "Do not adopt MD5 or SHA-1 for new signature or integrity uses."
    - "Do not leave DES/3DES/RC4, SSLv3 or TLS 1.0/1.1 in new configuration."
    - "Do not issue new RSA keys shorter than 2048 bits."
  prohibited:
    - "New MD5/SHA-1 use for signatures, MACs or integrity protection (non-security checksums without a 'non-security' note included)."
    - "New DES/3DES/RC4 encryption paths (DESede, ARCFOUR, crypto.createCipher(\"des\"), ...)."
    - "Server or CI deployment config that allows TLS 1.0/1.1 (old ssl_version / minVersion values)."
    - "New RSA-1024 or sha1WithRSA certificates or signing requests."
    - "Keeping legacy ciphers enabled by default for 'legacy compatibility' instead of isolating them."
---
# 枯れた暗号 — MD5/SHA1署名・DES系・TLS 1.0/1.1 を新規に書かない

> **適用条件**: ハッシュ・署名・暗号化・TLS設定に触れる場面すべて。
> 既存の使用箇所の棚卸しと置換も含む。
> 規模: 世界問題(枯れた暗号の残留は国境を問わず侵害の入口になるが、
> 義務の期限は国・調達ごとに異なる)。
> 要約: (1)MD5・SHA-1の署名/完全性用途の新規採用をしない
> (2)DES/3DES/RC4・SSLv3/TLS 1.0/1.1 を新規設定に残さない
> (3)RSA は 2048bit 未満を新規に発行しない。詳細は本文。

## 事実

NIST SP 800-131A Rev.2(2019)は SHA-1 署名を 2013 年末に失効扱いとし、
3DES は 2023 年末以降 disallowed とした。署名・鍵輸送の最低線は
RSA/DH 2048bit 以上、ECDSA 224bit 以上(FIPS 140-3 の承認算法と連動)。
SHA-1 の衝突攻撃 SHAttered(2017、Google/QuoVadis)は PDF 2 件の
同一ダイジェストを実証し、署名の実用性を崩した。MD5 衝突は 2004 年の
Wang らの報告以降、証明書偽造(Flame、2012)にも使われてきた。
TLS 側では POODLE(SSLv3、2014)、BEAST/CRIME 系を経て TLS 1.0/1.1 は
IETF RFC 8996(2021)で正式に非推奨化された。日本の CRYPTREC は
MD5/SHA-1 署名・RC4・64bit ブロック暗号を電子政府推奨リストから外し、
TLS は 1.2 以上 + 前方秘匿スイートを求める。EU CRA は脆弱性既知の
製品を市場に出すことを禁じ(附属書 I)、枯れた暗号は ENISA ガイダンスが
運用する「現状の技術水準(state of the art)」テストに落ちる。
出典: NIST SP 800-131A・CRYPTREC 電子政府推奨暗号リスト(sourcesに記録)。

## 禁止パターン

- 署名・MAC・完全性保護に MD5 / SHA-1 を新規採用する(チェックサム等の
  非セキュリティ用途も「非セキュリティ」注記なしで書く)。
- DES/3DES/RC4 の新規暗号化パス(`DESede` `ARCFOUR` `crypto.createCipher("des")` 等)。
- サーバ・CI 配備設定の TLS 1.0/1.1 許可(`ssl_version` `minVersion` の旧値)。
- RSA-1024・sha1WithRSA の新規証明書発行・署名要求。
- 「レガシー互換」の名目で既定に旧暗号を残す(隔離せずに有効化する)。

## 推奨設定

- ハッシュ: SHA-256 以上を既定に(署名は SHA-256withRSA/ECDSA 以上)。
- 共通鍵・鍵共有: AES-GCM/ChaCha20-Poly1305、鍵共有は ECDHE(新規は PQC 移行も検討。
  `baseline-pqc-fips` を参照)。
- TLS: 1.2 以上を最小にし、1.3 優先スイートを既定にする。
  非対応相手へのフォールバックは棚卸しで残存を追い、期限を切る。
- 非セキュリティ MD5(キャッシュキー、重複排除等)は呼び出し箇所に
  `non-security` / `checksum-only` の注記を残し、新規コードではより良い
  ハッシュ(XXH3/SHA-256-truncated 等)を検討する。
- レガシー読み込み互換が不可避な場合は明示の opt-in フラグ配下に隔離する。

具体例(悪い形と良い形の対):

```text
# 悪い: 枯れた暗号の新規採用
hashlib.md5(data)                    # 完全性用途。SHA-256 に
Cipher.getInstance("DESede")         # 3DES。AES-GCM に
ssl_version = TLSv1                  # TLS 1.0。TLSv1.2 以上に

# 良い: 現行の既定
hashlib.sha256(data)
Cipher.getInstance("AES/GCM/NoPadding")
ssl_version = TLSv1.2  # 可能なら TLSv1.3
```

## 運用チェック

- 暗号資産の棚卸し(どの鍵長・算法がどこで使われているか)を版管理し、
  PCI DSS 4.0(Req. 4.2.1)や調達要件の期限に照らした削除計画を持つ。
  担当: 依存管理と同じレビュー役。
- テストベクタ・fixture の MD5/SHA-1 は「既知回答としての用途」を
  コメントで明示し、運用コードへの混入を防ぐ。

## 制度変更ウォッチ

- 変更予告: NIST IR 8547 は RSA-2048・ECDH-P256 等の 112bit 安全性を
  2030 年までに deprecated、2035 年までに disallowed とする移行目標を示す
  (草案 ipd 段階)。確度: 審議中(最終版の確定要件を確認する)。
- 確認TODO: IR 8547 最終版の確定要件を一次で確認
  (review_by: 2027-03-31)。
- 影響TODO: 自プロジェクトの TLS 設定・証明書発行の最小線を
  (TLS 1.2+ / RSA-2048+)に固定し、CI で退行を検出する。

<!-- 法的助言ではない。専門家レビュー必須。 / This is not legal advice; expert review required. -->

<!-- © kanon contributors (https://github.com/politeuma/kanon). Section baseline-deprecated-crypto, licensed CC BY 4.0: https://creativecommons.org/licenses/by/4.0/ -->
