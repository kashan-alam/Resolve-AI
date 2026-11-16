import uuid

from sqlalchemy import Boolean, Index, Integer, JSON, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, uuid_column


class KnowledgeDocument(TimestampMixin, Base):
    __tablename__ = "knowledge_documents"
    __table_args__ = (
        UniqueConstraint(
            "document_key", "version", name="uq_knowledge_documents_key_version"
        ),
        Index(
            "uq_knowledge_documents_active_key",
            "document_key",
            unique=True,
            postgresql_where=text("is_active = true"),
        ),
    )

    id: Mapped[uuid.UUID] = uuid_column()
    document_key: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding_model: Mapped[str | None] = mapped_column(String(120))
    embedding_dimension: Mapped[int | None] = mapped_column(Integer)
    embedding_configuration: Mapped[dict | None] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    chunks = relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan"
    )
