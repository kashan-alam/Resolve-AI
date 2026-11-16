import uuid

from sqlalchemy import ForeignKey, Index, Integer, JSON, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from backend.app.models.base import Base, uuid_column


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint(
            "document_id", "chunk_index", name="uq_document_chunks_document_index"
        ),
        Index("ix_document_chunks_document_id", "document_id"),
    )

    id: Mapped[uuid.UUID] = uuid_column()
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_metadata: Mapped[dict | None] = mapped_column("metadata", JSON)
    embedding: Mapped[list[float]] = mapped_column(Vector(768), nullable=False)

    document = relationship("KnowledgeDocument", back_populates="chunks")
