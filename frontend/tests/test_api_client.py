from __future__ import annotations

import httpx
import pytest

from frontend.api_client import (
    ApiClientError,
    AuthenticationExpiredError,
    ResolveApiClient,
)


def _client(
    handler,
    *,
    token: str | None = None,
) -> tuple[ResolveApiClient, list[httpx.Request]]:
    requests: list[httpx.Request] = []
    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(base_url="http://backend", transport=transport)
    return ResolveApiClient(
        "http://backend",
        token=token,
        http_client=http_client,
    ), requests


def test_customer_message_uses_customer_scoped_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == (
            "/api/v1/customers/customer-a/conversations/conversation-1/messages"
        )
        assert request.read() == (
            b'{"customer_id":"customer-a","content":"Where is my order?"}'
        )
        return httpx.Response(200, json={"assistant_message": {"content": "Tracked"}})

    client, _ = _client(handler)
    try:
        result = client.send_message("customer-a", "conversation-1", "Where is my order?")
    finally:
        client.close()

    assert result["assistant_message"]["content"] == "Tracked"


def test_customer_and_conversation_requests_use_expected_routes() -> None:
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.url.path == "/api/v1/customers":
            return httpx.Response(200, json=[])
        if request.url.path == "/api/v1/conversations":
            return httpx.Response(201, json={"id": "conversation-1"})
        return httpx.Response(200, json=[])

    client, _ = _client(handler)
    try:
        client.list_customers()
        client.create_conversation("customer-a")
        client.list_conversations("customer-a")
        client.get_conversation("customer-a", "conversation-1")
    finally:
        client.close()

    assert paths == [
        "/api/v1/customers",
        "/api/v1/conversations",
        "/api/v1/customers/customer-a/conversations",
        "/api/v1/customers/customer-a/conversations/conversation-1",
    ]


def test_admin_login_and_ticket_update_use_authentication_contract() -> None:
    def login_handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/admin/login"
        assert request.read() == b'{"username":"admin","password":"secret"}'
        return httpx.Response(200, json={"access_token": "jwt", "token_type": "bearer"})

    client, _ = _client(login_handler)
    try:
        token_response = client.login("admin", "secret")
    finally:
        client.close()
    assert token_response["access_token"] == "jwt"

    def update_handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer jwt"
        assert request.url.path == "/api/v1/admin/tickets/ticket-1"
        assert request.read() == b'{"status":"resolved","resolution":"Done"}'
        return httpx.Response(200, json={"status": "resolved"})

    client, _ = _client(update_handler, token="jwt")
    try:
        result = client.update_ticket(
            "ticket-1",
            status="resolved",
            resolution="Done",
        )
    finally:
        client.close()
    assert result["status"] == "resolved"


def test_ticket_listing_sends_status_filter_and_bearer_token() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/admin/tickets"
        assert request.url.params["status"] == "open"
        assert request.headers["Authorization"] == "Bearer jwt"
        return httpx.Response(200, json=[])

    client, _ = _client(handler, token="jwt")
    try:
        assert client.list_tickets("open") == []
    finally:
        client.close()


def test_expired_admin_session_is_safe() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "private error"})

    client, _ = _client(handler, token="jwt")
    try:
        with pytest.raises(AuthenticationExpiredError, match="expired"):
            client.get_ticket("ticket-1")
    finally:
        client.close()


def test_connection_and_http_errors_do_not_expose_response_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"secret": "must not be shown"})

    client, _ = _client(handler)
    try:
        with pytest.raises(ApiClientError, match="HTTP 500") as error:
            client.list_customers()
    finally:
        client.close()
    assert "must not be shown" not in str(error.value)

    def failing_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("private connection details", request=request)

    client, _ = _client(failing_handler)
    try:
        with pytest.raises(ApiClientError, match="could not be reached"):
            client.list_customers()
    finally:
        client.close()
