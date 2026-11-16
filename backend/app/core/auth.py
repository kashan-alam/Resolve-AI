from __future__ import annotations

import hmac
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

from backend.app.core.config import settings


JWT_ALGORITHM = "HS256"
_password_hash = PasswordHash.recommended()


class AuthConfigurationError(RuntimeError):
    """Raised when required admin authentication configuration is absent."""


def _configured_authentication() -> tuple[str, str, str, int]:
    admin_username = settings.admin_username
    admin_password_hash = settings.admin_password_hash
    jwt_secret = settings.jwt_secret
    expiry_minutes = settings.jwt_expiry_minutes
    if (
        not admin_username
        or not admin_password_hash
        or not admin_password_hash.startswith("$argon2")
        or not jwt_secret
        or len(jwt_secret.encode("utf-8")) < 32
        or expiry_minutes is None
        or expiry_minutes <= 0
    ):
        raise AuthConfigurationError(
            "Admin authentication configuration is incomplete."
        )
    return admin_username, admin_password_hash, jwt_secret, expiry_minutes


def verify_admin_password(password: str) -> bool:
    _, password_hash, _, _ = _configured_authentication()
    try:
        return _password_hash.verify(password, password_hash)
    except UnknownHashError as error:
        raise AuthConfigurationError(
            "Admin authentication configuration is incomplete."
        ) from error
    except (TypeError, ValueError):
        return False


def authenticate_admin(username: str, password: str) -> bool:
    configured_username, _, _, _ = _configured_authentication()
    if not hmac.compare_digest(username, configured_username):
        return False
    return verify_admin_password(password)


def create_access_token(
    username: str,
    *,
    now: datetime | None = None,
    expires_in: timedelta | None = None,
) -> str:
    _, _, jwt_secret, expiry_minutes = _configured_authentication()
    issued_at = now or datetime.now(timezone.utc)
    lifetime = expires_in or timedelta(minutes=expiry_minutes)
    payload: dict[str, Any] = {
        "sub": username,
        "iat": issued_at,
        "exp": issued_at + lifetime,
        "type": "admin",
    }
    return jwt.encode(payload, jwt_secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, str]:
    configured_username, _, jwt_secret, _ = _configured_authentication()
    try:
        payload = jwt.decode(
            token,
            jwt_secret,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "iat", "exp"]},
        )
    except jwt.InvalidTokenError as error:
        raise ValueError("Invalid authentication token.") from error

    username = payload.get("sub")
    if (
        payload.get("type") != "admin"
        or not isinstance(username, str)
        or not hmac.compare_digest(username, configured_username)
    ):
        raise ValueError("Invalid authentication token.")
    return {"username": username}
