"""
Bonus requirement: verify that inbound webhook payloads genuinely originate
from Meta by recomputing the HMAC-SHA256 signature Meta attaches to every
request and comparing it (in constant time) against the X-Hub-Signature-256
header, using the WhatsApp App Secret as the key.

Docs: https://developers.facebook.com/docs/graph-api/webhooks/getting-started#validate-payloads
"""
from __future__ import annotations

import hashlib
import hmac
import logging

from app.config import get_settings

logger = logging.getLogger("app.security")


def verify_meta_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """
    Validates the X-Hub-Signature-256 header sent by Meta on every inbound
    webhook POST.  Returns True if the signature matches or if no app secret
    is configured (local dev / dry-run), False on any mismatch.
    """
    settings = get_settings()

    if not settings.whatsapp_app_secret:
        # No secret configured (e.g. local dev) - skip verification but be loud about it.
        logger.warning(
            "WHATSAPP_APP_SECRET not set - skipping webhook signature verification. "
            "Set it in production to prevent spoofed webhook deliveries."
        )
        return True

    if not signature_header or not signature_header.startswith("sha256="):
        logger.warning(
            "Missing or malformed X-Hub-Signature-256 header - rejecting payload"
        )
        return False

    # Compute expected HMAC-SHA256 using the app secret as the key.
    # Note: hmac.new() takes positional arguments (key, msg, digestmod).
    expected = hmac.new(
        settings.whatsapp_app_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    provided = signature_header.split("sha256=", 1)[1]

    # Use constant-time comparison to prevent timing attacks.
    if hmac.compare_digest(expected, provided):
        return True

    logger.warning(
        "X-Hub-Signature-256 mismatch - payload may have been tampered with "
        "(provided=%s…, expected=%s…)", provided[:12], expected[:12]
    )
    return False
