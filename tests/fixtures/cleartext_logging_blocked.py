"""MUST trigger the cleartext-PII gate: raw identifiers reach logging sinks."""

import logging

logger = logging.getLogger(__name__)


def handle_signup(email: str, request_body: dict) -> None:
    logger.info("new signup: %s", email)
    logger.error("signup failed for body %s", request_body)
