"""MUST trigger the deprecated-crypto gate: SHA-1 signatures and TLS 1.0 floor."""

import hashlib
import ssl

SSL_CONTEXT = ssl.SSLContext(ssl.PROTOCOL_TLSv1)


def sign(payload: bytes, key: bytes) -> str:
    digest = hashlib.sha1(payload).hexdigest()  # noqa: S324 - intentional fixture
    return digest + key.decode("utf-8", "replace")
