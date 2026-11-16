from __future__ import annotations

import uuid
from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.ai.embeddings import EmbeddingError, GeminiEmbedder
from backend.app.ai.generation import GenerationError
from backend.app.ai.orchestration import OrchestrationService
from backend.app.ai.schemas import Citation, IntentExtraction
from backend.app.models.conversation import Conversation
from backend.app.models.customer import Customer
from backend.app.models.message import Message
from backend.app.models.ticket import ACTIVE_TICKET_STATUSES, Ticket
from backend.app.models.ticket_event import TicketEvent
from backend.app.models.ticket_policy_evidence import TicketPolicyEvidence
from backend.app.rag.retriever import retrieve
from backend.app.tools.order_lookup import create_order_tool_registry
from backend.app.core.config import settings


class SupportWorkflowError(RuntimeError):
    """Raised when the support workflow cannot produce a safe response."""


@dataclass(frozen=True)
class WorkflowResult:
    customer_message: Message
    assistant_message: Message
    citations: list[Citation]
    order_result: dict[str, object] | None
    ticket: Ticket | None
    insufficient_evidence: bool


def persist_customer_message(
    session: Session, conversation: Conversation, content: str
) -> Message:
    message = Message(
        conversation_id=conversation.id,
        sender_type="customer",
        content=content,
    )
    session.add(message)
    session.commit()
    session.refresh(message)
    return message


def _prompt_for_intent(content: str) -> str:
    return (
        "Classify this ShopEase customer support message. "
        "Use only the allowed structured fields and do not invent facts.\n\n"
        f"Customer message:\n{content}"
    )


def _prompt_for_tool(content: str, extraction: IntentExtraction) -> str:
    return (
        "Select the order lookup tool for this ShopEase customer request. "
        "Provide only the order number from the customer message. "
        "The backend supplies customer ownership separately.\n\n"
        f"Message: {content}\n"
        f"Extracted order number: {extraction.order_number or 'none'}"
    )


def _policy_prompt(
    content: str,
    extraction: IntentExtraction,
    retrieved_chunks: list[dict[str, object]],
) -> str:
    evidence_context = "\n\n".join(
        f"Chunk ID: {chunk['chunk_id']}\nExcerpt:\n{chunk['chunk_text']}"
        for chunk in retrieved_chunks
    )
    return (
        "Answer the ShopEase customer using only the supplied retrieved policy "
        "evidence. Do not invent policy details. You must cite one or more "
        "exact Chunk ID strings from the context in the structured response "
        "field `citation_chunk_ids`.\n\n"
        f"Customer message: {content}\n"
        f"Intent category: {extraction.category.value}\n"
        f"Intent type: {extraction.issue_type.value}\n\n"
        f"Retrieved policy context:\n{evidence_context}"
    )


def _ticket_key(conversation_id: uuid.UUID, extraction: IntentExtraction) -> str:
    return (
        f"{conversation_id}:{extraction.category.value}:"
        f"{extraction.issue_type.value}"
    )


def _ticket_number() -> str:
    return f"T-{uuid.uuid4().hex[:12].upper()}"


def _escalation_reason(extraction: IntentExtraction) -> str:
    return (
        f"Human review required for {extraction.category.value}/"
        f"{extraction.issue_type.value}."
    )


def _get_or_create_ticket(
    session: Session,
    conversation: Conversation,
    customer: Customer,
    extraction: IntentExtraction,
    citations: list[Citation],
) -> Ticket:
    issue_key = _ticket_key(conversation.id, extraction)
    ticket = session.scalar(
        select(Ticket).where(
            Ticket.issue_key == issue_key,
            Ticket.status.in_(ACTIVE_TICKET_STATUSES),
        )
    )
    if ticket is None:
        ticket = Ticket(
            ticket_number=_ticket_number(),
            conversation_id=conversation.id,
            customer_id=customer.id,
            category=extraction.category.value,
            issue_type=extraction.issue_type.value,
            issue_key=issue_key,
            priority="normal",
            status="pending_human_review",
            escalation_reason=_escalation_reason(extraction),
            ai_summary="Customer request requires human review.",
            extracted_information={
                "order_number": extraction.order_number,
                "product": extraction.product,
            },
            requires_human_review=True,
        )
        session.add(ticket)
        session.flush()
        session.add(
            TicketEvent(
                ticket_id=ticket.id,
                event_type="created",
                new_value="pending_human_review",
            )
        )

    for citation in citations:
        session.add(
            TicketPolicyEvidence(
                ticket_id=ticket.id,
                document_id=citation.document_id,
                chunk_id=citation.chunk_id,
                document_title=citation.document_title,
                chunk_text=citation.chunk_text,
                evidence_classification="sufficient",
            )
        )
    return ticket


def _assistant_text_for_order(result: dict[str, object]) -> str:
    if not result.get("found"):
        return (
            "I could not find that order for the selected demo customer. "
            "Please check the order number."
        )
    return (
        f"Order {result['order_number']} for {result['product']} is "
        f"{result['order_status']}. Payment status: {result['payment_status']}. "
        f"Order date: {result['order_date']}."
    )


def _retrieve_policy(
    session: Session,
    embedder: GeminiEmbedder | None,
    orchestration: OrchestrationService,
    content: str,
    extraction: IntentExtraction,
) -> tuple[str, list[Citation], bool]:
    if embedder is None:
        raise SupportWorkflowError("Policy embedding is unavailable.")
    query_embedding = embedder.embed(content)
    evidence = retrieve(
        session,
        query_embedding,
        dimension=embedder.dimension,
        top_k=settings.rag_top_k,
        threshold=settings.rag_similarity_threshold,
    )
    if evidence.classification != "sufficient":
        return (
            "I could not find enough information in the ShopEase policy "
            "documents to answer that safely. A support specialist can help.",
            [],
            True,
        )
    chunks = list(evidence.chunks)
    draft, citations = orchestration.draft_policy_response(
        _policy_prompt(content, extraction, chunks),
        chunks,
    )
    return draft.message, citations, False


def process_support_message(
    session: Session,
    customer: Customer,
    conversation: Conversation,
    content: str,
    orchestration: OrchestrationService,
    embedder: GeminiEmbedder | None,
    customer_message: Message | None = None,
) -> WorkflowResult:
    if customer_message is None:
        customer_message = persist_customer_message(session, conversation, content)
    try:
        extraction = orchestration.extract(
            _prompt_for_intent(content), IntentExtraction
        )
        citations: list[Citation] = []
        order_result: dict[str, object] | None = None
        insufficient_evidence = False
        ticket_required = (
            extraction.human_support_requested
            or extraction.requested_action.value == "human_support"
        )

        if extraction.needs_clarification:
            response_text = extraction.clarification_question or (
                "Could you provide a little more information so I can help?"
            )
        elif (
            extraction.requested_action.value == "order_lookup"
            or extraction.order_number
        ):
            registry = create_order_tool_registry(session, customer.id)
            order_orchestration = OrchestrationService(
                orchestration.generation, registry
            )
            tool_result = order_orchestration.request_tool(
                _prompt_for_tool(content, extraction)
            )
            order_result = tool_result.data
            response_text = _assistant_text_for_order(order_result)
        else:
            response_text, citations, insufficient_evidence = _retrieve_policy(
                session, embedder, orchestration, content, extraction
            )
            ticket_required = ticket_required or insufficient_evidence

        session.rollback()
        with session.begin():
            ticket = (
                _get_or_create_ticket(
                    session, conversation, customer, extraction, citations
                )
                if ticket_required
                else None
            )
            assistant_message = Message(
                conversation_id=conversation.id,
                sender_type="assistant",
                content=response_text,
            )
            session.add(assistant_message)
            session.flush()
            session.refresh(assistant_message)
        return WorkflowResult(
            customer_message=customer_message,
            assistant_message=assistant_message,
            citations=citations,
            order_result=order_result,
            ticket=ticket,
            insufficient_evidence=insufficient_evidence,
        )
    except (
        EmbeddingError,
        GenerationError,
        SQLAlchemyError,
        SupportWorkflowError,
        ValueError,
    ) as error:
        session.rollback()
        raise SupportWorkflowError(
            "The support request could not be completed safely."
        ) from error
