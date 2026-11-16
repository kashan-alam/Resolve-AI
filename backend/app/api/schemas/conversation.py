from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConversationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_id: uuid.UUID


class ConversationSummary(BaseModel):
    model_config = ConfigDict(strict=True)

    id: uuid.UUID
    customer_id: uuid.UUID
    status: str
    created_at: datetime


class MessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_id: uuid.UUID
    content: str = Field(min_length=1, max_length=10_000)


class MessageResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_type: str
    content: str
    created_at: datetime


class ConversationDetail(ConversationSummary):
    messages: list[MessageResponse]
    ticket: ConversationTicketSummary | None = None


class ConversationTicketSummary(BaseModel):
    model_config = ConfigDict(strict=True)

    ticket_number: str
    status: str


class PolicyCitationResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_key: str
    document_title: str
    document_version: int
    category: str
    chunk_index: int
    chunk_text: str


class MessageWorkflowResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    message: MessageResponse
    assistant_message: MessageResponse
    policy_citations: list[PolicyCitationResponse] = Field(default_factory=list)
    order_result: dict[str, object] | None = None
    ticket: TicketWorkflowSummary | None = None
    insufficient_evidence: bool = False


class TicketWorkflowSummary(BaseModel):
    model_config = ConfigDict(strict=True)

    id: uuid.UUID
    ticket_number: str
    status: str
    escalation_reason: str | None
