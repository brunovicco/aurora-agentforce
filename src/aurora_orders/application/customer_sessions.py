"""Short-lived, signed customer context supplied by a trusted upstream channel.

The module verifies context; it does not authenticate a customer or expose a
public token-issuing endpoint. Never let the LLM choose or mint these claims.
"""

import base64
import hashlib
import hmac
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

ISSUER = "aurora-trusted-channel"
AUDIENCE = "aurora-orders"
MAX_SESSION_SECONDS = 900
TOKEN_MAX_LENGTH = 4096
CLAIMS = frozenset({"v", "iss", "aud", "sub", "sid", "iat", "exp"})
OPAQUE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
BASE64_URL = re.compile(r"^[A-Za-z0-9_-]+$")


class InvalidCustomerSession(ValueError):
    """A customer context is missing, malformed, untrusted, or no longer valid."""


@dataclass(frozen=True, slots=True)
class VerifiedCustomer:
    """Customer identity and session ID vouched for by a trusted issuer."""

    customer_ref: str
    session_id: str


def validate_signing_key(signing_key: str) -> bytes:
    """Require a different high-entropy secret from the integration API key."""
    if len(signing_key.strip()) < 32:
        raise ValueError("AURORA_CUSTOMER_SESSION_SECRET must contain at least 32 characters.")
    return signing_key.encode("utf-8")


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64decode(text: str) -> bytes:
    if not BASE64_URL.fullmatch(text):
        raise InvalidCustomerSession
    try:
        raw = base64.b64decode(
            text + "=" * (-len(text) % 4), altchars=b"-_", validate=True
        )
    except (ValueError, base64.binascii.Error) as error:
        raise InvalidCustomerSession from error
    if _b64encode(raw) != text:
        raise InvalidCustomerSession
    return raw


def _utc_timestamp(now: datetime) -> int:
    if now.tzinfo is None:
        raise ValueError("Session time must be timezone-aware.")
    return int(now.astimezone(UTC).timestamp())


def mint_demo_session(
    *,
    signing_key: str,
    customer_ref: str,
    session_id: str,
    now: datetime,
    ttl_seconds: int = 300,
) -> str:
    """Issue a token for tests or trusted *offline* demo tooling only.

    This helper is NOT a proof-of-identity step or a public customer login API.
    """
    key = validate_signing_key(signing_key)
    if not OPAQUE_ID.fullmatch(customer_ref) or not OPAQUE_ID.fullmatch(session_id):
        raise ValueError("Use nonempty opaque customer and session identifiers.")
    if not 1 <= ttl_seconds <= MAX_SESSION_SECONDS:
        raise ValueError("Session TTL must be between 1 and 900 seconds.")
    issued_at = _utc_timestamp(now)
    claims = {
        "v": 1,
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": customer_ref,
        "sid": session_id,
        "iat": issued_at,
        "exp": issued_at + ttl_seconds,
    }
    payload = _b64encode(json.dumps(claims, sort_keys=True, separators=(",", ":")).encode())
    signature = _b64encode(hmac.new(key, payload.encode("ascii"), hashlib.sha256).digest())
    return f"{payload}.{signature}"


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, value in pairs:
        if name in result:
            raise InvalidCustomerSession
        result[name] = value
    return result


def verify_customer_session(
    token: str,
    *,
    signing_key: str,
    now: datetime,
    revoked_session_ids: frozenset[str] = frozenset(),
) -> VerifiedCustomer:
    """Verify the trusted issuer, signed subject, TTL and local revocation set."""
    key = validate_signing_key(signing_key)
    if not token or len(token) > TOKEN_MAX_LENGTH or token.count(".") != 1:
        raise InvalidCustomerSession
    payload, signature = token.split(".", maxsplit=1)
    supplied = _b64decode(signature)
    expected = hmac.new(key, payload.encode("ascii"), hashlib.sha256).digest()
    if not hmac.compare_digest(supplied, expected):
        raise InvalidCustomerSession
    try:
        claims = json.loads(_b64decode(payload), object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise InvalidCustomerSession from error
    if not isinstance(claims, dict) or claims.keys() != CLAIMS:
        raise InvalidCustomerSession
    if (
        type(claims["v"]) is not int
        or claims["v"] != 1
        or claims["iss"] != ISSUER
        or claims["aud"] != AUDIENCE
        or type(claims["sub"]) is not str
        or not OPAQUE_ID.fullmatch(claims["sub"])
        or type(claims["sid"]) is not str
        or not OPAQUE_ID.fullmatch(claims["sid"])
        or type(claims["iat"]) is not int
        or type(claims["exp"]) is not int
    ):
        raise InvalidCustomerSession
    issued_at = claims["iat"]
    expires_at = claims["exp"]
    current = _utc_timestamp(now)
    if (
        issued_at > current
        or expires_at <= current
        or not 1 <= expires_at - issued_at <= MAX_SESSION_SECONDS
        or claims["sid"] in revoked_session_ids
    ):
        raise InvalidCustomerSession
    return VerifiedCustomer(customer_ref=claims["sub"], session_id=claims["sid"])
