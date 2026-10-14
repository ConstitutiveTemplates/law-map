---
id: baseline-pqc-fips
version: "2026-09-21.1"
status: active
placement: agents_md
when: [library, cli, web_api]
obligations:
  - obligation.crypto.no-deprecated-algorithms
triggers:
  keywords: ["pqc", "fips", "tls", "rsa", "ecdh", "ecdsa", "kyber", "ml-kem"]
  pattern: '(?i)\b(ml-kem|ml-dsa|slh-dsa|kyber|dilithium|sphincs|fips\s?20[345]|rsa|ecdh|ecdsa|ed25519|tls|ssl|kem|cipher|pqc|post-quantum)\b'
  config: '(?i)\b(ml-kem|ml-dsa|slh-dsa|kyber|dilithium|sphincs|fips\s?20[345]|rsa|ecdh|ecdsa|tls)\b'
sources:
  - https://www.nist.gov/news-events/news/2024/08/nist-releases-first-3-finalized-post-quantum-encryption-standards
  - https://csrc.nist.gov/pubs/fips/203/final
  - https://csrc.nist.gov/pubs/fips/204/final
  - https://csrc.nist.gov/pubs/fips/205/final
  - https://csrc.nist.gov/pubs/ir/8547/ipd
license: CC-BY-4.0
en:
  title: "PQC standards — choose ML-KEM/ML-DSA and hybrids for new cryptography"
  summary:
    - "Use the standard names (ML-KEM, ML-DSA, SLH-DSA), not submission names such as Kyber."
    - "Key establishment uses ML-KEM; signatures default to ML-DSA with SLH-DSA as the conservative alternative; do not mix the roles."
    - "Migrate via hybrids (X25519MLKEM768, ...); do not adopt classical algorithms alone in new designs."
  prohibited:
    - "RSA key transport (RSA/ECB/PKCS1Padding, ...), ECDH-only key agreement or RSA/ECDSA-only signatures in new code."
    - "New use of submission names (kyber768, dilithium3, ...) in settings or identifiers."
    - "Mixing roles (signing with a KEM, key agreement with a signature algorithm)."
    - "Making SLH-DSA the default (bandwidth and certificate-size cost; keep it for conservative uses)."
    - "Encrypting long-lived data or issuing long-lived tokens/certificates with a quantum-vulnerable algorithm alone."
---
# PQC標準 — 新規の暗号選択はML-KEM/ML-DSA系・ハイブリッドで行う

> **適用条件**: TLS・鍵交換・署名・証明書・JWT・VPNなど暗号プリミティブを
> 新規に選択・実装・設定する場面すべて。保守で暗号まわりを触る時も含む。
> 規模: 世界問題(旧暗号は今も全世界で書かれ、被害は保存データとして長期化する)。
> 要約: (1)標準名で呼ぶ(ML-KEM/ML-DSA/SLH-DSA。応募名Kyber等を新規に使わない)
> (2)鍵共有はKEM=ML-KEM、署名はML-DSAが既定・SLH-DSAは保守的代替と役割を混ぜない
> (3)移行はハイブリッド(X25519MLKEM768等)で行い、旧暗号単独の新規採用をしない。
> 詳細は本文。

## 事実

NISTは2024-08-13、耐量子暗号の正式標準3件を発行した。
FIPS 203 = ML-KEM(鍵カプセル化KEM、CRYSTALS-Kyber由来)、
FIPS 204 = ML-DSA(デジタル署名、CRYSTALS-Dilithium由来。第一選択の既定)、
FIPS 205 = SLH-DSA(署名、SPHINCS+由来。格子前提に依存しない保守的代替)。
3規格は相互互換の選択肢ではなく機能が異なる: ML-KEMは鍵共有専用で署名を持たず、
RSA鍵交換/ECDHを代替する。ML-DSAとSLH-DSAは署名専用で、RSA署名/ECDSAを代替する。
SLH-DSAは安全性をハッシュのみに負う反面、署名が約7.9KB(128s)〜17.1KB(128f)と
巨大で、ML-DSA-44の約2.4KBに比べ通信帯域・ログ・証明書チェーンを圧迫する。
NIST IR 8547はRSA-2048・ECDH-P256等の112bit安全性を2030年までにdeprecated、
2035年までにdisallowedとする移行目標を示した。長期秘匿データは
「今盗聴→後で量子解読」(harvest now, decrypt later)の対象になるため、
移行期限は保存データの秘匿が必要な期間から逆算する。
出典: NIST FIPS 203/204/205・IR 8547(sourcesに記録)。

## 禁止パターン

- 新規コードでのRSA鍵輸送(`RSA/ECB/PKCS1Padding`等)・ECDH単独の鍵共有・
  RSA/ECDSA単独の新規署名設計。
- 応募名の新規採用(`kyber768` `dilithium3`等の設定値・識別子。標準名に直す)。
- 役割の混同(KEMで署名する、署名アルゴリズムで鍵共有する)。
- SLH-DSAのデフォルト採用(帯域・証明書サイズの肥大化。保守的用途に限定)。
- 量子脆弱アルゴリズム単体での長期保存データ暗号化・長期有効なトークン/証明書。

## 推奨設定

- TLS: ハイブリッド群を優先(`X25519MLKEM768`。OpenSSL 3.5系は既定の群に組み込み)。
  非対応相手へは従来群にフォールバックしつつ、棚卸しで残存接続を追跡する。
- 署名/PKI: 新規はML-DSAを既定に。SLH-DSAは帯域に余裕のある保守的な用途のみ。
  移行期は従来署名との二重署名で検証側の互換を取り、composite署名の標準化を追う。
- ライブラリ: 標準名API(`ML-KEM-768`等)を提供する版に上げ、独自実装をしない。
- 用語の移行: ドキュメント・設定・ログの応募名を標準名に置換し、
  対応はIANA等の公式レジストリで確認する。

具体例(設定・識別子に現れる形。悪い形と良い形の対):

```text
# 悪い: 応募名と旧単体の新規採用
kyber768 / dilithium3                  # 応募名。標準名に直す
TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256  # ECDH 単独の新規鍵共有

# 良い: 標準名 + ハイブリッド
ML-KEM-768(鍵共有) / ML-DSA-65(署名)     # FIPS 203/204 の標準名
group = X25519MLKEM768                  # TLS のハイブリッド群(OpenSSL 3.5系は既定群)
```

## 運用チェック

- 暗号資産棚卸し(どの鍵長・アルゴリズムがどこで使われているか)を版管理し、
  IR 8547の2030/2035里程碑に照らした削除計画を持つ。担当: 依存管理と同じ
  レビュー役(単独では回らない)。
- JWT・mTLS・VPN等のプロファイルごとに移行可否を確認する。標準団体の
  プロファイル更新待ちの箇所は「待ち」と明示して無理に繋がない。

## 制度変更ウォッチ

- 変更予告: FIPS 206(FN-DSA、Falcon由来)は草案待ち。確度: 審議中。
  CNSA 2.0等の政府調達スケジュールは民間標準より前倒し。
- 確認TODO: IR 8547最終版(草案ipdからfinal化)の確定要件を一次で確認
  (review_by: 2027-03-31)。
- 影響TODO: 自プロジェクトが依存する暗号ライブラリのML-KEM/ML-DSA対応版を
  確認し、pinを外して追従できる状態にしておく。

<!-- 法的助言ではない。専門家レビュー必須。 / This is not legal advice; expert review required. -->

<!-- © kanon contributors (https://github.com/politeuma/kanon). Section baseline-pqc-fips, licensed CC BY 4.0: https://creativecommons.org/licenses/by/4.0/ -->
