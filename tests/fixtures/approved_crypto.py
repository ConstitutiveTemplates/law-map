"""MUST NOT trigger the deprecated-crypto gate: SHA-256 with TLS 1.2+."""

import hashlib
import ssl

SSL_CONTEXT = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


def sign(payload: bytes) -> str:
    return hashlib.sha256(payload, usedforsecurity=True).hexdigest()
