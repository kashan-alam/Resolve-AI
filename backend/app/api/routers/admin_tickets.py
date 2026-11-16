import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_current_admin
from backend.app.api.schemas.conversation import MessageResponse
from backend.app.api.schemas.ticket import (
    AdminTicketDetail,
    TicketEventResponse,
    TicketEvidenceResponse,
    TicketStatus,
    TicketSummary,
    TicketUpdateRequest,
)
from backend.app.core.database import get_db
from backend.app.services.ticket_service import (
    TicketNotFoundError,
    get_ticket,
    list_tickets,
    update_ticket,
)


admin_ticket_router = APIRouter(
    prefix="/admin/tickets",
    tags=["admin-tickets"],
    dependencies=[Depends(get_current_admin)],
)


def _summary(ticket) -> TicketSummary:
    return TicketSummary(
        id=ticket.id,
        ticket_number=ticket.ticket_number,
        conversation_id=ticket.conversation_id,
        customer_id=ticket.customer_id,
        order_id=ticket.order_id,
        category=ticket.category,
        issue_type=ticket.issue_type,
        status=ticket.status,
        requires_human_review=ticket.requires_human_review,
        created_at=ticket.created_at,
    )


def _detail(ticket) -> AdminTicketDetail:
    return AdminTicketDetail(
        **_summary(ticket).model_dump(),
        priority=ticket.priority,
        escalation_reason=ticket.escalation_reason,
        final_response=ticket.final_response,
        messages=[
            MessageResponse(
                id=message.id,
                conversation_id=message.conversation_id,
                sender_type=message.sender_type,
                content=message.content,
                created_at=message.created_at,
            )
            for message in ticket.conversation.messages
        ],
        events=[
            TicketEventResponse(
                id=event.id,
                event_type=event.event_type,
                old_value=event.old_value,
                new_value=event.new_value,
                internal_note=event.internal_note,
                created_at=event.created_at,
            )
            for event in ticket.events
        ],
        evidence=[
            TicketEvidenceResponse(
                id=item.id,
                document_id=item.document_id,
                chunk_id=item.chunk_id,
                document_title=item.document_title,
                chunk_text=item.chunk_text,
                similarity_score=(
                    float(item.similarity_score)
                    if item.similarity_score is not None
                    else None
                ),
                evidence_classification=item.evidence_classification,
                created_at=item.created_at,
            )
            for item in ticket.evidence
        ],
    )


@admin_ticket_router.get("", response_model=list[TicketSummary])
def list_admin_tickets(
    ticket_status: TicketStatus | None = Query(default=None, alias="status"),
    session: Session = Depends(get_db),
) -> list[TicketSummary]:
    return [_summary(ticket) for ticket in list_tickets(session, ticket_status)]


@admin_ticket_router.get("/{ticket_id}", response_model=AdminTicketDetail)
def get_admin_ticket(
    ticket_id: uuid.UUID,
    session: Session = Depends(get_db),
) -> AdminTicketDetail:
    try:
        return _detail(get_ticket(session, ticket_id))
    except TicketNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found.",
        ) from error


@admin_ticket_router.patch(
    "/{ticket_id}",
    response_model=AdminTicketDetail,
)
def update_admin_ticket(
    ticket_id: uuid.UUID,
    request: TicketUpdateRequest,
    session: Session = Depends(get_db),
) -> AdminTicketDetail:
    try:
        return _detail(update_ticket(session, ticket_id, request))
    except TicketNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found.",
        ) from error
