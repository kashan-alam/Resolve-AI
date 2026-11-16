from dataclasses import replace
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from pwdlib import PasswordHash

from backend.app.api import routers
from backend.app.core import auth
from backend.app.core.config import settings
from backend.app.main import app


@pytest.fixture
def configured_auth(monkeypatch: pytest.MonkeyPatch) -> str:
    password_hash = PasswordHash.recommended().hash("correct-password")
    configured = replace(
        settings,
        admin_username="demo-admin",
        admin_password_hash=password_hash,
        jwt_secret="test-secret-for-hs256-unit-tests-32",
        jwt_expiry_minutes=15,
    )
    monkeypatch.setattr(auth, "settings", configured)
    monkeypatch.setattr(routers, "settings", configured)
    return password_hash


def test_password_hash_verification(configured_auth: str) -> None:
    assert auth.verify_admin_password("correct-password") is True
    assert auth.verify_admin_password("wrong-password") is False


def test_token_contains_required_claims(configured_auth: str) -> None:
    token = auth.create_access_token("demo-admin")

    payload = jwt.decode(
        token,
        "test-secret-for-hs256-unit-tests-32",
        algorithms=["HS256"],
        options={"require": ["sub", "iat", "exp"]},
    )

    assert payload["sub"] == "demo-admin"
    assert payload["type"] == "admin"
    assert payload["exp"] > payload["iat"]


def test_expired_token_is_rejected(configured_auth: str) -> None:
    token = auth.create_access_token(
        "demo-admin",
        now=datetime.now(timezone.utc) - timedelta(minutes=2),
        expires_in=timedelta(minutes=1),
    )

    with pytest.raises(ValueError, match="Invalid authentication token"):
        auth.decode_access_token(token)


def test_invalid_signature_and_malformed_token_are_rejected(
    configured_auth: str,
) -> None:
    token = auth.create_access_token("demo-admin")

    with pytest.raises(ValueError):
        auth.decode_access_token(token + "tampered")
    with pytest.raises(ValueError):
        auth.decode_access_token("not-a-jwt")


def test_incorrect_jwt_type_is_rejected(configured_auth: str) -> None:
    token = jwt.encode(
        {
            "sub": "demo-admin",
            "type": "customer",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        "test-secret-for-hs256-unit-tests-32",
        algorithm="HS256",
    )

    with pytest.raises(ValueError, match="Invalid authentication token"):
        auth.decode_access_token(token)


def test_different_admin_identity_is_rejected(configured_auth: str) -> None:
    token = auth.create_access_token("different-admin")

    with pytest.raises(ValueError, match="Invalid authentication token"):
        auth.decode_access_token(token)


def test_missing_auth_configuration_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unconfigured = replace(
        settings,
        admin_username=None,
        admin_password_hash=None,
        jwt_secret=None,
        jwt_expiry_minutes=None,
    )
    monkeypatch.setattr(auth, "settings", unconfigured)
    monkeypatch.setattr(routers, "settings", unconfigured)

    with pytest.raises(auth.AuthConfigurationError):
        auth.authenticate_admin("demo-admin", "password")


def test_missing_auth_configuration_returns_http_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unconfigured = replace(
        settings,
        admin_username=None,
        admin_password_hash=None,
        jwt_secret=None,
        jwt_expiry_minutes=None,
    )
    monkeypatch.setattr(auth, "settings", unconfigured)
    monkeypatch.setattr(routers, "settings", unconfigured)

    response = TestClient(app).post(
        "/api/v1/admin/login",
        json={"username": "demo-admin", "password": "password"},
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Admin authentication is unavailable."
    }


def test_malformed_argon2_hash_returns_http_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configured = replace(
        settings,
        admin_username="demo-admin",
        admin_password_hash="$argon2malformed",
        jwt_secret="test-secret-for-hs256-unit-tests-32",
        jwt_expiry_minutes=15,
    )
    monkeypatch.setattr(auth, "settings", configured)
    monkeypatch.setattr(routers, "settings", configured)

    response = TestClient(app).post(
        "/api/v1/admin/login",
        json={"username": "demo-admin", "password": "password"},
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Admin authentication is unavailable."
    }


def test_weak_jwt_secret_returns_http_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    password_hash = PasswordHash.recommended().hash("correct-password")
    configured = replace(
        settings,
        admin_username="demo-admin",
        admin_password_hash=password_hash,
        jwt_secret="weak-secret",
        jwt_expiry_minutes=15,
    )
    monkeypatch.setattr(auth, "settings", configured)
    monkeypatch.setattr(routers, "settings", configured)

    response = TestClient(app).post(
        "/api/v1/admin/login",
        json={"username": "demo-admin", "password": "correct-password"},
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Admin authentication is unavailable."
    }


def test_admin_login_and_protected_endpoint(configured_auth: str) -> None:
    client = TestClient(app)

    login = client.post(
        "/api/v1/admin/login",
        json={"username": "demo-admin", "password": "correct-password"},
    )

    assert login.status_code == 200
    token = login.json()["access_token"]
    response = client.get(
        "/api/v1/admin/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {"username": "demo-admin"}


def test_invalid_admin_login_is_rejected(configured_auth: str) -> None:
    response = TestClient(app).post(
        "/api/v1/admin/login",
        json={"username": "demo-admin", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid admin credentials."}


@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Bearer malformed-token"}],
)
def test_protected_endpoint_rejects_missing_or_invalid_token(
    configured_auth: str,
    headers: dict[str, str],
) -> None:
    response = TestClient(app).get("/api/v1/admin/me", headers=headers)

    assert response.status_code == 401


def test_health_endpoint_remains_available_without_auth_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unconfigured = replace(
        settings,
        admin_username=None,
        admin_password_hash=None,
        jwt_secret=None,
        jwt_expiry_minutes=None,
    )
    monkeypatch.setattr(auth, "settings", unconfigured)
    monkeypatch.setattr(routers, "settings", unconfigured)

    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
