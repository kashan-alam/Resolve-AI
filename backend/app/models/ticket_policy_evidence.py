import uuid
from decimal import Decimal
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, uuid_column


class TicketPolicyEvidence(Base):
    __tablename__ = "ticket_policy_evidence"

    id: Mapped[uuid.UUID] = uuid_column()
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("knowledge_documents.id", ondelete="SET NULL"), index=True
    )
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("document_chunks.id", ondelete="SET NULL"), index=True
    )
    document_title: Mapped[str] = mapped_column(String(200), nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    similarity_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    evidence_classification: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    ticket = relationship("Ticket", back_populates="evidence")
