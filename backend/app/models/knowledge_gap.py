import uuid

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, uuid_column


class KnowledgeGap(TimestampMixin, Base):
    __tablename__ = "knowledge_gaps"

    id: Mapped[uuid.UUID] = uuid_column()
    normalized_question: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    example_question: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    approved_answer: Mapped[str | None] = mapped_column(Text)

    tickets = relationship(
        "Ticket",
        secondary="knowledge_gap_tickets",
        back_populates="knowledge_gaps",
    )
