import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, uuid_column


ACTIVE_TICKET_STATUSES = (
    "open",
    "pending_human_review",
    "assigned",
    "in_progress",
)


class Ticket(TimestampMixin, Base):
    __tablename__ = "tickets"
    __table_args__ = (
        UniqueConstraint("ticket_number", name="uq_tickets_ticket_number"),
        Index(
            "uq_tickets_active_issue_key",
            "issue_key",
            unique=True,
            postgresql_where=text(
                "status IN ('open', 'pending_human_review', 'assigned', 'in_progress')"
            ),
        ),
        Index("ix_tickets_status_created_at", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = uuid_column()
    ticket_number: Mapped[str] = mapped_column(String(32), nullable=False)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), index=True
    )
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    issue_type: Mapped[str] = mapped_column(String(32), nullable=False)
    issue_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="normal")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    escalation_reason: Mapped[str | None] = mapped_column(Text)
    assigned_team: Mapped[str | None] = mapped_column(String(32))
    ai_summary: Mapped[str | None] = mapped_column(Text)
    extracted_information: Mapped[dict | None] = mapped_column(JSON)
    ai_suggested_resolution: Mapped[str | None] = mapped_column(Text)
    ai_draft_response: Mapped[str | None] = mapped_column(Text)
    final_response: Mapped[str | None] = mapped_column(Text)
    requires_human_review: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    conversation = relationship("Conversation", back_populates="tickets")
    customer = relationship("Customer", back_populates="tickets")
    order = relationship("Order", back_populates="tickets")
    events = relationship(
        "TicketEvent", back_populates="ticket", cascade="all, delete-orphan"
    )
    evidence = relationship(
        "TicketPolicyEvidence", back_populates="ticket", cascade="all, delete-orphan"
    )
    knowledge_gaps = relationship(
        "KnowledgeGap",
        secondary="knowledge_gap_tickets",
        back_populates="tickets",
    )
