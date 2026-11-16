import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.ai.embeddings import create_configured_embedder
from backend.app.ai.embeddings import EmbeddingError
from backend.app.ai.generation import GenerationError, GenerationService
from backend.app.ai.orchestration import OrchestrationService
from backend.app.api.schemas.conversation import (
    ConversationCreate,
    ConversationDetail,
    ConversationSummary,
    ConversationTicketSummary,
    MessageCreate,
    MessageResponse,
    MessageWorkflowResponse,
    PolicyCitationResponse,
    TicketWorkflowSummary,
)
from backend.app.api.schemas.customer import CustomerSummary
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.models.conversation import Conversation
from backend.app.models.customer import Customer
from backend.app.models.message import Message
from backend.app.services.support_workflow import (
    SupportWorkflowError,
    persist_customer_message,
    process_support_message,
)
from backend.app.tools.registry import ToolRegistry


customer_router = APIRouter(tags=["customer"])
logger = logging.getLogger(__name__)


def _customer_or_404(session: Session, customer_id: uuid.UUID) -> Customer:
    customer = session.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found.",
        )
    return customer


def _conversation_or_404(
    session: Session, conversation_id: uuid.UUID, customer_id: uuid.UUID
) -> Conversation:
    conversation = session.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.customer_id == customer_id,
        )
    )
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )
    return conversation


def _message_response(message: Message) -> MessageResponse:
    return MessageResponse(
        id=message.id,
        conversation_id=message.conversation_id,
        sender_type=message.sender_type,
        content=message.content,
        created_at=message.created_at,
    )


def _conversation_summary(conversation: Conversation) -> ConversationSummary:
    return ConversationSummary(
        id=conversation.id,
        customer_id=conversation.customer_id,
        status=conversation.status,
        created_at=conversation.created_at,
    )


def _latest_ticket(conversation: Conversation) -> ConversationTicketSummary | None:
    if not conversation.tickets:
        return None
    ticket = max(
        conversation.tickets,
        key=lambda item: (item.created_at, str(item.id)),
    )
    return ConversationTicketSummary(
        ticket_number=ticket.ticket_number,
        status=ticket.status,
    )


@customer_router.get("/customers", response_model=list[CustomerSummary])
def list_customers(session: Session = Depends(get_db)) -> list[CustomerSummary]:
    customers = session.scalars(select(Customer).order_by(Customer.name)).all()
    return [
        CustomerSummary(id=item.id, name=item.name, email=item.email)
        for item in customers
    ]


@customer_router.post(
    "/conversations",
    response_model=ConversationSummary,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(
    request: ConversationCreate,
    session: Session = Depends(get_db),
) -> ConversationSummary:
    customer = _customer_or_404(session, request.customer_id)
    conversation = Conversation(customer_id=customer.id, status="active")
    session.add(conversation)
    session.commit()
    session.refresh(conversation)
    return _conversation_summary(conversation)


@customer_router.get(
    "/customers/{customer_id}/conversations",
    response_model=list[ConversationSummary],
)
def list_conversations(
    customer_id: uuid.UUID,
    session: Session = Depends(get_db),
) -> list[ConversationSummary]:
    _customer_or_404(session, customer_id)
    conversations = session.scalars(
        select(Conversation)
        .where(Conversation.customer_id == customer_id)
        .order_by(Conversation.created_at)
    ).all()
    return [_conversation_summary(item) for item in conversations]


@customer_router.get(
    "/customers/{customer_id}/conversations/{conversation_id}",
    response_model=ConversationDetail,
)
def get_conversation(
    customer_id: uuid.UUID,
    conversation_id: uuid.UUID,
    session: Session = Depends(get_db),
) -> ConversationDetail:
    conversation = _conversation_or_404(session, conversation_id, customer_id)
    messages = session.scalars(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at, Message.id)
    ).all()
    return ConversationDetail(
        **_conversation_summary(conversation).model_dump(),
        messages=[_message_response(message) for message in messages],
        ticket=_latest_ticket(conversation),
    )


@customer_router.post(
    "/customers/{customer_id}/conversations/{conversation_id}/messages",
    response_model=MessageWorkflowResponse,
)
def send_message(
    customer_id: uuid.UUID,
    conversation_id: uuid.UUID,
    request: MessageCreate,
    session: Session = Depends(get_db),
) -> MessageWorkflowResponse:
    if request.customer_id != customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customer does not own this conversation.",
        )
    customer = _customer_or_404(session, customer_id)
    conversation = _conversation_or_404(session, conversation_id, customer_id)
    customer_message = persist_customer_message(
        session, conversation, request.content
    )
    try:
        generation = GenerationService(
            api_key=settings.gemini_api_key or "",
            model=settings.gemini_generation_model,
        )
        embedder = None
        if settings.gemini_api_key:
            embedder = create_configured_embedder()
        result = process_support_message(
            session,
            customer,
            conversation,
            request.content,
            OrchestrationService(generation, ToolRegistry()),
            embedder,
            customer_message=customer_message,
        )
    except (EmbeddingError, GenerationError) as error:
        logger.exception(
            "Customer support failed: exception_type=%s exception_message=%s",
            type(error).__name__,
            str(error)[:500],
        )
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The support request could not be completed safely.",
        ) from error
    except SupportWorkflowError as error:
        logger.exception(
            "Customer support workflow failed: exception_type=%s "
            "exception_message=%s",
            type(error).__name__,
            str(error)[:500],
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The support request could not be completed safely.",
        ) from error
    return MessageWorkflowResponse(
        message=_message_response(result.customer_message),
        assistant_message=_message_response(result.assistant_message),
        policy_citations=[
            PolicyCitationResponse(**citation.model_dump())
            for citation in result.citations
        ],
        order_result=result.order_result,
        ticket=(
            TicketWorkflowSummary(
                id=result.ticket.id,
                ticket_number=result.ticket.ticket_number,
                status=result.ticket.status,
                escalation_reason=result.ticket.escalation_reason,
            )
            if result.ticket
            else None
        ),
        insufficient_evidence=result.insufficient_evidence,
    )
