"""MUST NOT trigger the cleartext-PII gate: identifiers are masked before logging."""

import logging

logger = logging.getLogger(__name__)


def _mask(email: str) -> str:
    local, _, domain = email.partition("@")
    return f"{local[:1]}***@{domain}"


def handle_signup(email: str) -> None:
    logger.info("new signup: %s", _mask(email))  # masked
