from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Table, Column, func

from backend.app.models.base import Base


knowledge_gap_tickets = Table(
    "knowledge_gap_tickets",
    Base.metadata,
    Column(
        "knowledge_gap_id",
        ForeignKey("knowledge_gaps.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "ticket_id",
        ForeignKey("tickets.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)
