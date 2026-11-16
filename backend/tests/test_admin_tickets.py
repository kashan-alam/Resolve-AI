from dataclasses import replace
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from backend.app.api.routers import admin_tickets
from backend.app.api.schemas.ticket import TicketStatus, TicketUpdateRequest
from backend.app.core import auth
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.main import app
from backend.app.models.ticket import Ticket
from backend.app.services.ticket_service import update_ticket


class TransactionSession:
    def __init__(self, ticket: Ticket, fail_on_flush: bool = False) -> None:
        self.ticket = ticket
        self.fail_on_flush = fail_on_flush
        self.added: list[object] = []
        self.commit_count = 0
        self.rollback_count = 0

    def begin(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.commit_count += 1
        else:
            self.rollback_count += 1
        return False

    def get(self, model, ticket_id):
        return self.ticket

    def add(self, value: object) -> None:
        self.added.append(value)

    def flush(self) -> None:
        if self.fail_on_flush:
            raise RuntimeError("forced database failure")


def _ticket() -> Ticket:
    return Ticket(
        id=__import__("uuid").uuid4(),
        ticket_number="T-123",
        conversation_id=__import__("uuid").uuid4(),
        customer_id=__import__("uuid").uuid4(),
        category="other",
        issue_type="unknown",
        issue_key="conversation:other:unknown",
        priority="normal",
        status="open",
        requires_human_review=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def test_admin_ticket_list_requires_authentication() -> None:
    response = TestClient(app).get("/api/v1/admin/tickets")

    assert response.status_code == 401


def test_authenticated_admin_can_list_tickets_with_status_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configured = replace(
        settings,
        admin_username="demo-admin",
        admin_password_hash="$argon2id$test",
        jwt_secret="test-secret-for-hs256-unit-tests-32",
        jwt_expiry_minutes=15,
    )
    monkeypatch.setattr(auth, "settings", configured)
    monkeypatch.setattr(
        admin_tickets,
        "list_tickets",
        lambda session, status: [_ticket()],
    )

    class FakeDatabase:
        pass

    def override_get_db():
        yield FakeDatabase()

    app.dependency_overrides[get_db] = override_get_db
    try:
        token = auth.create_access_token("demo-admin")
        response = TestClient(app).get(
            "/api/v1/admin/tickets?status=open",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert response.json()[0]["status"] == "open"


def test_status_change_records_event_and_timestamps() -> None:
    ticket = _ticket()
    session = TransactionSession(ticket)

    updated = update_ticket(
        session,
        ticket.id,
        TicketUpdateRequest(status=TicketStatus.RESOLVED),
    )

    assert updated.status == "resolved"
    assert updated.resolved_at is not None
    assert updated.closed_at is None
    assert len(session.added) == 1
    assert session.added[0].event_type == "status_changed"
    assert session.commit_count == 1


def test_note_and_resolution_updates_record_events() -> None:
    ticket = _ticket()
    session = TransactionSession(ticket)

    update_ticket(
        session,
        ticket.id,
        TicketUpdateRequest(
            internal_note="Reviewed evidence.",
            resolution="Customer was informed of the resolution.",
        ),
    )

    assert ticket.final_response == "Customer was informed of the resolution."
    assert [event.event_type for event in session.added] == [
        "internal_note_added",
        "resolution_updated",
    ]


def test_same_status_does_not_create_status_event() -> None:
    ticket = _ticket()
    session = TransactionSession(ticket)

    update_ticket(
        session,
        ticket.id,
        TicketUpdateRequest(status=TicketStatus.OPEN),
    )

    assert session.added == []
    assert session.commit_count == 1


def test_update_failure_rolls_back_transaction() -> None:
    ticket = _ticket()
    session = TransactionSession(ticket, fail_on_flush=True)

    with pytest.raises(RuntimeError):
        update_ticket(
            session,
            ticket.id,
            TicketUpdateRequest(
                status=TicketStatus.CLOSED,
                resolution="Closed after review.",
            ),
        )

    assert session.commit_count == 0
    assert session.rollback_count == 1
