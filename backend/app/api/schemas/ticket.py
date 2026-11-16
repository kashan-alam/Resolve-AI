import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TicketStatus(StrEnum):
    OPEN = "open"
    PENDING_HUMAN_REVIEW = "pending_human_review"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketSummary(BaseModel):
    model_config = ConfigDict(strict=True)

    id: uuid.UUID
    ticket_number: str
    conversation_id: uuid.UUID
    customer_id: uuid.UUID
    order_id: uuid.UUID | None
    category: str
    issue_type: str
    status: str
    requires_human_review: bool
    created_at: datetime


class TicketUpdateRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    status: TicketStatus | None = None
    internal_note: str | None = Field(default=None, min_length=1, max_length=10_000)
    resolution: str | None = Field(default=None, min_length=1, max_length=10_000)

    @model_validator(mode="after")
    def require_update(self) -> "TicketUpdateRequest":
        if self.status is None and self.internal_note is None and self.resolution is None:
            raise ValueError("At least one ticket update is required.")
        return self


class TicketEventResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    id: uuid.UUID
    event_type: str
    old_value: str | None
    new_value: str | None
    internal_note: str | None
    created_at: datetime


class TicketEvidenceResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    id: uuid.UUID
    document_id: uuid.UUID | None
    chunk_id: uuid.UUID | None
    document_title: str
    chunk_text: str
    similarity_score: float | None
    evidence_classification: str
    created_at: datetime


class AdminTicketDetail(TicketSummary):
    priority: str
    escalation_reason: str | None
    final_response: str | None
    messages: list["MessageResponse"]
    events: list[TicketEventResponse]
    evidence: list[TicketEvidenceResponse]


from backend.app.api.schemas.conversation import MessageResponse
