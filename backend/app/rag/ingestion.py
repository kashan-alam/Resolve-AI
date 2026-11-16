import hashlib
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.ai.embeddings import normalize_embedding
from backend.app.models.document_chunk import DocumentChunk
from backend.app.models.knowledge_document import KnowledgeDocument
from backend.app.rag.chunker import TextChunk, chunk_text


@dataclass(frozen=True)
class DocumentInput:
    document_key: str
    title: str
    filename: str
    category: str
    content: str


@dataclass(frozen=True)
class IngestionConfig:
    embedding_model: str
    embedding_dimension: int
    embedding_configuration: dict
    chunk_token_limit: int = 1800
    chunk_overlap_tokens: int = 150
    chunking_version: str = "token-regex-v1"

    def as_metadata(self) -> dict:
        return {
            **self.embedding_configuration,
            "chunk_token_limit": self.chunk_token_limit,
            "chunk_overlap_tokens": self.chunk_overlap_tokens,
            "chunking_version": self.chunking_version,
        }


@dataclass(frozen=True)
class PreparedDocument:
    source: DocumentInput
    source_hash: str
    chunks: tuple[TextChunk, ...]
    vectors: tuple[list[float], ...]


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _same_processing_config(
    document: KnowledgeDocument,
    source_hash: str,
    config: IngestionConfig,
) -> bool:
    return (
        document.content_hash == source_hash
        and document.embedding_model == config.embedding_model
        and document.embedding_dimension == config.embedding_dimension
        and document.embedding_configuration == config.as_metadata()
    )


def is_document_unchanged(
    document: KnowledgeDocument,
    source: DocumentInput,
    config: IngestionConfig,
) -> bool:
    return _same_processing_config(document, content_hash(source.content), config)


def prepare_document(
    source: DocumentInput,
    embedder,
    config: IngestionConfig,
) -> PreparedDocument:
    chunks = tuple(
        chunk_text(
            source.content,
            max_tokens=config.chunk_token_limit,
            overlap_tokens=config.chunk_overlap_tokens,
        )
    )
    if not chunks:
        raise ValueError("Cannot ingest an empty document.")
    vectors = tuple(
        normalize_embedding(embedder.embed(chunk.text), config.embedding_dimension)
        for chunk in chunks
    )
    return PreparedDocument(
        source=source,
        source_hash=content_hash(source.content),
        chunks=chunks,
        vectors=vectors,
    )


def prepare_documents(
    sources: list[DocumentInput],
    embedder,
    config: IngestionConfig,
) -> list[PreparedDocument]:
    return [prepare_document(source, embedder, config) for source in sources]


def persist_prepared_document(
    session: Session,
    prepared: PreparedDocument,
    config: IngestionConfig,
) -> KnowledgeDocument:
    source = prepared.source
    active = session.scalar(
        select(KnowledgeDocument).where(
            KnowledgeDocument.document_key == source.document_key,
            KnowledgeDocument.is_active.is_(True),
        )
    )
    if active and _same_processing_config(
        active,
        prepared.source_hash,
        config,
    ):
        return active

    next_version = (
        session.scalar(
            select(KnowledgeDocument.version)
            .where(KnowledgeDocument.document_key == source.document_key)
            .order_by(KnowledgeDocument.version.desc())
            .limit(1)
        )
        or 0
    ) + 1
    document = KnowledgeDocument(
        document_key=source.document_key,
        title=source.title,
        filename=source.filename,
        category=source.category,
        content=source.content,
        content_hash=prepared.source_hash,
        version=next_version,
        embedding_model=config.embedding_model,
        embedding_dimension=config.embedding_dimension,
        embedding_configuration=config.as_metadata(),
        is_active=False,
    )
    session.add(document)
    session.flush()
    for chunk, vector in zip(prepared.chunks, prepared.vectors, strict=True):
        session.add(
            DocumentChunk(
                document_id=document.id,
                chunk_index=chunk.index,
                chunk_text=chunk.text,
                chunk_metadata={
                    "document_key": source.document_key,
                    "document_version": next_version,
                    "title": source.title,
                    "filename": source.filename,
                    "category": source.category,
                    "token_count": chunk.token_count,
                },
                embedding=vector,
            )
        )
    if active:
        active.is_active = False
        session.flush()
    document.is_active = True
    return document


def persist_prepared_documents(
    session: Session,
    prepared_documents: list[PreparedDocument],
    config: IngestionConfig,
) -> list[KnowledgeDocument]:
    return [
        persist_prepared_document(session, prepared, config)
        for prepared in prepared_documents
    ]


def ingest_documents(
    session: Session,
    sources: list[DocumentInput],
    embedder,
    config: IngestionConfig,
) -> list[KnowledgeDocument]:
    changed_sources = []
    for source in sources:
        active = session.scalar(
            select(KnowledgeDocument).where(
                KnowledgeDocument.document_key == source.document_key,
                KnowledgeDocument.is_active.is_(True),
            )
        )
        if not active or not is_document_unchanged(active, source, config):
            changed_sources.append(source)

    prepared = prepare_documents(changed_sources, embedder, config)
    return persist_prepared_documents(session, prepared, config)


def ingest_document(
    session: Session,
    source: DocumentInput,
    embedder,
    config: IngestionConfig,
) -> KnowledgeDocument:
    """Prepare a document replacement within the caller-owned transaction.

    The caller must commit after successful validation and roll back if this
    function or a later flush raises. No database changes are committed here.
    """
    source_hash = content_hash(source.content)
    active = session.scalar(
        select(KnowledgeDocument).where(
            KnowledgeDocument.document_key == source.document_key,
            KnowledgeDocument.is_active.is_(True),
        )
    )
    if active and _same_processing_config(active, source_hash, config):
        return active

    prepared = prepare_document(source, embedder, config)
    return persist_prepared_document(session, prepared, config)
