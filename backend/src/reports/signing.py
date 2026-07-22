"""Signed, expiring tokens for shareable report links - HMAC-SHA256 over
`{report_id}:{expires_at}`, not a general-purpose auth scheme (this app has no auth; see
app/core/workspace.py). Only used to prove a link was minted by this server and hasn't
expired, so a report can be shared outside the app without exposing the workspace header.
"""

import base64
import hashlib
import hmac
import time

from app.core.config import settings

DEFAULT_TTL_SECONDS = 7 * 24 * 3600  # 7 days


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def _sign(payload: bytes) -> bytes:
    return hmac.new(settings.SECRET_KEY.encode("utf-8"), payload, hashlib.sha256).digest()


def sign_report_id(report_id: str, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> tuple[str, int]:
    """Returns (token, expires_at_epoch_seconds)."""
    expires_at = int(time.time()) + ttl_seconds
    payload = f"{report_id}:{expires_at}".encode("utf-8")
    token = f"{_b64url_encode(payload)}.{_b64url_encode(_sign(payload))}"
    return token, expires_at


def verify_signed_token(token: str, expected_report_id: str) -> bool:
    """True if `token` is a validly-signed, unexpired token for `expected_report_id`."""
    try:
        payload_b64, signature_b64 = token.split(".", 1)
        payload = _b64url_decode(payload_b64)
        signature = _b64url_decode(signature_b64)
    except Exception:  # noqa: BLE001 - malformed input at a trust boundary fails closed
        return False

    if not hmac.compare_digest(signature, _sign(payload)):
        return False

    report_id, _, expires_at_str = payload.decode("utf-8").partition(":")
    if report_id != expected_report_id or not expires_at_str.isdigit():
        return False
    return int(expires_at_str) >= int(time.time())
