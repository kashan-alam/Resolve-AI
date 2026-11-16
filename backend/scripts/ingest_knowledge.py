"""Prepare and atomically ingest the approved ShopEase policy corpus."""

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select

from backend.app.ai.embeddings import create_configured_embedder
from backend.app.core.config import settings
from backend.app.models.knowledge_document import KnowledgeDocument
from backend.app.rag.document_loader import load_document
from backend.app.rag.ingestion import (
    DocumentInput,
    IngestionConfig,
    is_document_unchanged,
    persist_prepared_documents,
    prepare_documents,
)

APPROVED_EMBEDDING_MODEL = "gemini-embedding-001"
APPROVED_EMBEDDING_DIMENSION = 768


@dataclass(frozen=True)
class PolicyDocumentSpec:
    filename: str
    document_key: str
    title: str
    category: str


APPROVED_DOCUMENTS = (
    PolicyDocumentSpec(
        filename="return_policy.md",
        document_key="return_policy",
        title="ShopEase Returns Policy",
        category="returns",
    ),
    PolicyDocumentSpec(
        filename="refund_policy.md",
        document_key="refund_policy",
        title="ShopEase Refund Policy",
        category="refunds",
    ),
    PolicyDocumentSpec(
        filename="shipping_policy.md",
        document_key="shipping_policy",
        title="ShopEase Shipping Policy",
        category="shipping",
    ),
    PolicyDocumentSpec(
        filename="warranty_policy.md",
        document_key="warranty_policy",
        title="ShopEase Warranty and Product Issues Policy",
        category="warranty",
    ),
    PolicyDocumentSpec(
        filename="faq.md",
        document_key="faq",
        title="ShopEase Frequently Asked Questions",
        category="other",
    ),
)


def ingestion_config() -> IngestionConfig:
    return IngestionConfig(
        embedding_model=APPROVED_EMBEDDING_MODEL,
        embedding_dimension=APPROVED_EMBEDDING_DIMENSION,
        embedding_configuration={
            "output_dimensionality": APPROVED_EMBEDDING_DIMENSION
        },
        chunk_token_limit=settings.rag_chunk_token_limit,
        chunk_overlap_tokens=settings.rag_chunk_overlap_tokens,
    )


def load_approved_documents() -> list[DocumentInput]:
    directory = Path(__file__).resolve().parents[1] / "knowledge_base"
    documents = []
    for spec in APPROVED_DOCUMENTS:
        path = directory / spec.filename
        content, _ = load_document(path)
        documents.append(
            DocumentInput(
                document_key=spec.document_key,
                title=spec.title,
                filename=spec.filename,
                category=spec.category,
                content=content,
            )
        )
    return documents


def get_session_local():
    from backend.app.core.database import SessionLocal

    return SessionLocal


def main() -> int:
    session_local = get_session_local()
    if session_local is None:
        raise RuntimeError("DATABASE_URL is required for knowledge ingestion.")

    sources = load_approved_documents()
    config = ingestion_config()

    with session_local() as read_session:
        changed_sources = [
            source
            for source in sources
            if not (
                active := read_session.scalar(
                    select(KnowledgeDocument).where(
                        KnowledgeDocument.document_key == source.document_key,
                        KnowledgeDocument.is_active.is_(True),
                    )
                )
            )
            or not is_document_unchanged(active, source, config)
        ]

    prepared = []
    if changed_sources:
        embedder = create_configured_embedder()
        prepared = prepare_documents(changed_sources, embedder, config)

    with session_local.begin() as session:
        persisted = persist_prepared_documents(session, prepared, config)

    for document in persisted:
        print(
            f"Prepared document {document.document_key} version {document.version}."
        )
    if not persisted:
        print("All approved policy documents are unchanged; nothing to ingest.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
