"""HTTP client for the ResolveAI FastAPI backend."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx


class ApiClientError(Exception):
    """A safe, user-facing API client error."""


class AuthenticationExpiredError(ApiClientError):
    """The admin session is no longer valid."""


class ResolveApiClient:
    """Small client that keeps frontend code independent from HTTP details."""

    def __init__(
        self,
        base_url: str,
        *,
        token: str | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        normalized_url = base_url.strip().rstrip("/")
        if not normalized_url:
            raise ValueError("A backend API URL is required.")
        self._client = http_client or httpx.Client(
            base_url=normalized_url,
            timeout=httpx.Timeout(10.0),
        )
        self._owns_client = http_client is None
        self._token = token

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def list_customers(self) -> list[dict[str, Any]]:
        return self._request("GET", "/api/v1/customers")

    def create_conversation(self, customer_id: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/v1/conversations",
            json={"customer_id": customer_id},
        )

    def list_conversations(self, customer_id: str) -> list[dict[str, Any]]:
        return self._request(
            "GET",
            f"/api/v1/customers/{customer_id}/conversations",
        )

    def get_conversation(
        self, customer_id: str, conversation_id: str
    ) -> dict[str, Any]:
        return self._request(
            "GET",
            f"/api/v1/customers/{customer_id}/conversations/{conversation_id}",
        )

    def send_message(
        self,
        customer_id: str,
        conversation_id: str,
        content: str,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/api/v1/customers/{customer_id}/conversations/{conversation_id}/messages",
            json={"customer_id": customer_id, "content": content},
        )

    def login(self, username: str, password: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/v1/admin/login",
            json={"username": username, "password": password},
        )

    def list_tickets(self, status: str | None = None) -> list[dict[str, Any]]:
        params = {"status": status} if status else None
        return self._request(
            "GET",
            "/api/v1/admin/tickets",
            params=params,
            authenticated=True,
        )

    def get_ticket(self, ticket_id: str) -> dict[str, Any]:
        return self._request(
            "GET",
            f"/api/v1/admin/tickets/{ticket_id}",
            authenticated=True,
        )

    def update_ticket(
        self,
        ticket_id: str,
        *,
        status: str | None = None,
        internal_note: str | None = None,
        resolution: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            key: value
            for key, value in {
                "status": status,
                "internal_note": internal_note,
                "resolution": resolution,
            }.items()
            if value is not None
        }
        return self._request(
            "PATCH",
            f"/api/v1/admin/tickets/{ticket_id}",
            json=payload,
            authenticated=True,
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Mapping[str, Any] | None = None,
        params: Mapping[str, str] | None = None,
        authenticated: bool = False,
    ) -> Any:
        headers = {}
        if authenticated:
            if not self._token:
                raise AuthenticationExpiredError("Your admin session has expired.")
            headers["Authorization"] = f"Bearer {self._token}"

        try:
            response = self._client.request(
                method,
                path,
                headers=headers,
                json=json,
                params=params,
            )
        except httpx.RequestError as error:
            raise ApiClientError(
                "The backend could not be reached. Check that it is running."
            ) from error

        if response.status_code == 401 and authenticated:
            raise AuthenticationExpiredError(
                "Your admin session has expired. Please log in again."
            )
        if response.status_code >= 400:
            raise ApiClientError(_safe_status_message(response.status_code))

        try:
            return response.json()
        except ValueError as error:
            raise ApiClientError("The backend returned an invalid response.") from error


def _safe_status_message(status_code: int) -> str:
    if status_code == 404:
        return "The requested resource was not found."
    if status_code in (502, 503, 504):
        return "The backend service is temporarily unavailable."
    return f"The backend request failed (HTTP {status_code})."
