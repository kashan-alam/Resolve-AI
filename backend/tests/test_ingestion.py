import uuid
import math

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.ai.embeddings import EmbeddingError
from backend.app.models.document_chunk import DocumentChunk
from backend.app.models.knowledge_document import KnowledgeDocument
from backend.app.rag.ingestion import (
    DocumentInput,
    IngestionConfig,
    ingest_document,
)


class FakeEmbedder:
    def __init__(self, value: float = 1.0) -> None:
        self.value = value
        self.calls = 0

    def embed(self, text: str) -> list[float]:
        self.calls += 1
        return [self.value] * 768


class FailingEmbedder:
    def embed(self, text: str) -> list[float]:
        raise EmbeddingError("synthetic embedding failure")


class InvalidEmbedder:
    def __init__(self, vector: list[float]) -> None:
        self.vector = vector

    def embed(self, text: str) -> list[float]:
        return self.vector


def _config() -> IngestionConfig:
    return IngestionConfig(
        embedding_model="gemini-embedding-001",
        embedding_dimension=768,
        embedding_configuration={"output_dimensionality": 768},
        chunk_token_limit=40,
        chunk_overlap_tokens=5,
    )


def _source(content: str) -> DocumentInput:
    return DocumentInput(
        document_key=f"test-document-{uuid.uuid4()}",
        title="Test document",
        filename="test.md",
        category="test",
        content=content,
    )


def test_unchanged_document_skips_embedding(database_session: Session) -> None:
    source = _source("A short policy document.")
    embedder = FakeEmbedder()

    first = ingest_document(database_session, source, embedder, _config())
    database_session.flush()
    second = ingest_document(database_session, source, embedder, _config())

    assert first.id == second.id
    assert embedder.calls == 1


def test_changed_document_replaces_active_version(database_session: Session) -> None:
    source = _source("The first policy version.")
    embedder = FakeEmbedder()
    first = ingest_document(database_session, source, embedder, _config())
    database_session.flush()

    replacement = DocumentInput(
        document_key=source.document_key,
        title=source.title,
        filename=source.filename,
        category=source.category,
        content="The replacement policy version.",
    )
    second = ingest_document(database_session, replacement, embedder, _config())
    database_session.flush()

    assert first.version == 1
    assert second.version == 2
    assert first.is_active is False
    assert second.is_active is True
    active = database_session.scalars(
        select(KnowledgeDocument).where(
            KnowledgeDocument.document_key == source.document_key,
            KnowledgeDocument.is_active.is_(True),
        )
    ).all()
    assert [document.id for document in active] == [second.id]


def test_embedding_failure_preserves_previous_active_version(
    database_session: Session,
) -> None:
    source = _source("The working policy version.")
    working = ingest_document(database_session, source, FakeEmbedder(), _config())
    database_session.flush()

    changed = DocumentInput(
        document_key=source.document_key,
        title=source.title,
        filename=source.filename,
        category=source.category,
        content="A failed replacement.",
    )
    with pytest.raises(EmbeddingError):
        ingest_document(database_session, changed, FailingEmbedder(), _config())

    assert working.is_active is True


def test_ingestion_normalizes_vectors_before_persistence(
    database_session: Session,
) -> None:
    source = _source("A deliberately non-normalized embedding.")
    document = ingest_document(
        database_session,
        source,
        FakeEmbedder(value=2.0),
        _config(),
    )
    database_session.flush()

    vector = database_session.scalar(
        select(DocumentChunk.embedding).where(
            DocumentChunk.document_id == document.id
        )
    )

    assert vector is not None
    assert math.isclose(
        math.sqrt(sum(value * value for value in vector)), 1.0, abs_tol=1e-6
    )


@pytest.mark.parametrize(
    "vector",
    [
        [1.0],
        [float("nan")] * 768,
        [0.0] * 768,
    ],
)
def test_ingestion_rejects_invalid_vectors(
    database_session: Session, vector: list[float]
) -> None:
    with pytest.raises(EmbeddingError):
        ingest_document(
            database_session,
            _source("An invalid embedding."),
            InvalidEmbedder(vector),
            _config(),
        )


def test_database_failure_rolls_back_document_replacement(
    database_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _source("The active policy version.")
    working = ingest_document(database_session, source, FakeEmbedder(), _config())
    database_session.flush()

    original_flush = database_session.flush
    flush_count = 0

    def fail_replacement_flush(*args, **kwargs):
        nonlocal flush_count
        flush_count += 1
        if flush_count == 2:
            raise RuntimeError("simulated replacement flush failure")
        return original_flush(*args, **kwargs)

    monkeypatch.setattr(database_session, "flush", fail_replacement_flush)
    replacement = DocumentInput(
        document_key=source.document_key,
        title=source.title,
        filename=source.filename,
        category=source.category,
        content="The replacement policy version.",
    )

    with pytest.raises(RuntimeError, match="simulated replacement flush failure"):
        with database_session.begin_nested():
            ingest_document(database_session, replacement, FakeEmbedder(), _config())

    documents = database_session.scalars(
        select(KnowledgeDocument).where(
            KnowledgeDocument.document_key == source.document_key
        )
    ).all()
    chunks = database_session.scalars(
        select(DocumentChunk).where(
            DocumentChunk.document_id != working.id
        )
    ).all()

    assert len(documents) == 1
    assert documents[0].id == working.id
    assert documents[0].is_active is True
    assert chunks == []
