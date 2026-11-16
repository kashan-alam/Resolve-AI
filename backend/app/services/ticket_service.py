from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.schemas.ticket import TicketStatus, TicketUpdateRequest
from backend.app.models.ticket import Ticket
from backend.app.models.ticket_event import TicketEvent


class TicketNotFoundError(LookupError):
    """Raised when an admin requests a ticket that does not exist."""


def list_tickets(
    session: Session, status: TicketStatus | None = None
) -> list[Ticket]:
    statement = select(Ticket).order_by(Ticket.created_at.desc())
    if status is not None:
        statement = statement.where(Ticket.status == status.value)
    return list(session.scalars(statement).all())


def get_ticket(session: Session, ticket_id: uuid.UUID) -> Ticket:
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise TicketNotFoundError
    return ticket


def update_ticket(
    session: Session,
    ticket_id: uuid.UUID,
    request: TicketUpdateRequest,
) -> Ticket:
    with session.begin():
        ticket = session.get(Ticket, ticket_id)
        if ticket is None:
            raise TicketNotFoundError

        if request.status is not None and request.status.value != ticket.status:
            old_status = ticket.status
            new_status = request.status.value
            ticket.status = new_status
            now = datetime.now(timezone.utc)
            if new_status == TicketStatus.RESOLVED.value:
                ticket.resolved_at = now
                ticket.closed_at = None
            elif new_status == TicketStatus.CLOSED.value:
                ticket.resolved_at = ticket.resolved_at or now
                ticket.closed_at = now
            else:
                ticket.resolved_at = None
                ticket.closed_at = None
            session.add(
                TicketEvent(
                    ticket_id=ticket.id,
                    event_type="status_changed",
                    old_value=old_status,
                    new_value=new_status,
                )
            )

        if request.internal_note is not None:
            session.add(
                TicketEvent(
                    ticket_id=ticket.id,
                    event_type="internal_note_added",
                    internal_note=request.internal_note,
                )
            )

        if request.resolution is not None:
            ticket.final_response = request.resolution
            session.add(
                TicketEvent(
                    ticket_id=ticket.id,
                    event_type="resolution_updated",
                    new_value=request.resolution,
                )
            )

        session.flush()
    return ticket
