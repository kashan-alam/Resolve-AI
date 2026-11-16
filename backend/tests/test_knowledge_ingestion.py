import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from backend.app.ai.embeddings import EmbeddingError
from backend.app.models.document_chunk import DocumentChunk
from backend.app.models.knowledge_document import KnowledgeDocument
from backend.scripts import ingest_knowledge
from backend.app.rag.ingestion import (
    DocumentInput,
    IngestionConfig,
    ingest_documents,
    persist_prepared_documents,
    prepare_documents,
)


class FakeEmbedder:
    def __init__(self, value: float = 1.0) -> None:
        self.value = value
        self.calls = 0

    def embed(self, text: str) -> list[float]:
        self.calls += 1
        return [self.value] * 768


class DimensionEmbedder:
    def __init__(self, dimension: int) -> None:
        self.dimension = dimension
        self.calls = 0

    def embed(self, text: str) -> list[float]:
        self.calls += 1
        return [1.0] * self.dimension


class InvalidEmbedder:
    def embed(self, text: str) -> list[float]:
        return [0.0] * 768


class FailingEmbedder:
    def embed(self, text: str) -> list[float]:
        raise EmbeddingError("synthetic embedding failure")


def _config(
    *,
    dimension: int = 768,
    chunk_token_limit: int = 40,
    chunk_overlap_tokens: int = 5,
    configuration_marker: str | None = None,
) -> IngestionConfig:
    embedding_configuration = {"output_dimensionality": dimension}
    if configuration_marker is not None:
        embedding_configuration["task_type"] = configuration_marker
    return IngestionConfig(
        embedding_model="gemini-embedding-001",
        embedding_dimension=dimension,
        embedding_configuration=embedding_configuration,
        chunk_token_limit=chunk_token_limit,
        chunk_overlap_tokens=chunk_overlap_tokens,
    )


def _source(content: str, key: str | None = None) -> DocumentInput:
    return DocumentInput(
        document_key=key or f"test-document-{uuid.uuid4()}",
        title="Test document",
        filename="test.md",
        category="test",
        content=content,
    )


def _ingest(session: Session, sources, embedder, config):
    return ingest_documents(session, sources, embedder, config)


def _documents(session: Session, key: str):
    return session.scalars(
        select(KnowledgeDocument)
        .where(KnowledgeDocument.document_key == key)
        .order_by(KnowledgeDocument.version)
    ).all()


def test_initial_ingestion_creates_active_document_and_chunks(database_session):
    source = _source("Initial policy content.")
    documents = _ingest(database_session, [source], FakeEmbedder(), _config())
    database_session.flush()

    assert documents[0].version == 1
    assert documents[0].is_active is True
    assert database_session.scalar(
        select(DocumentChunk).where(DocumentChunk.document_id == documents[0].id)
    )


def test_idempotent_reingestion_skips_embedding(database_session):
    source = _source("Unchanged policy content.")
    embedder = FakeEmbedder()
    _ingest(database_session, [source], embedder, _config())
    database_session.flush()
    documents = _documents(database_session, source.document_key)

    _ingest(database_session, [source], embedder, _config())
    database_session.flush()

    assert embedder.calls == 1
    assert len(_documents(database_session, source.document_key)) == 1
    assert documents[0].is_active is True


def test_content_change_creates_new_version(database_session):
    source = _source("The original policy content.")
    _ingest(database_session, [source], FakeEmbedder(), _config())
    database_session.flush()
    replacement = _source("The revised policy content.", key=source.document_key)

    _ingest(database_session, [replacement], FakeEmbedder(), _config())
    database_session.flush()

    documents = _documents(database_session, source.document_key)
    assert [document.version for document in documents] == [1, 2]
    assert documents[0].content == source.content
    assert documents[0].is_active is False
    assert documents[1].content == replacement.content
    assert documents[1].is_active is True


@pytest.mark.parametrize(
    "config_factory",
    [
        lambda: _config(configuration_marker="retrieval_query"),
        lambda: _config(chunk_token_limit=10, chunk_overlap_tokens=2),
    ],
)
def test_processing_configuration_change_creates_new_version(
    database_session, config_factory
):
    source = _source("A policy with enough content to exercise processing changes.")
    _ingest(database_session, [source], FakeEmbedder(), _config())
    database_session.flush()
    embedder = FakeEmbedder()

    changed_config = config_factory()
    _ingest(database_session, [source], embedder, changed_config)
    database_session.flush()

    documents = _documents(database_session, source.document_key)
    assert [document.version for document in documents] == [1, 2]
    assert documents[0].is_active is False
    assert documents[1].is_active is True
    assert embedder.calls > 0


def test_embedding_model_change_triggers_reembedding(database_session):
    source = _source("Embedding configuration content.")
    _ingest(database_session, [source], FakeEmbedder(), _config())
    database_session.flush()
    config = IngestionConfig(
        embedding_model="different-embedding-model",
        embedding_dimension=768,
        embedding_configuration={"output_dimensionality": 768},
        chunk_token_limit=40,
        chunk_overlap_tokens=5,
    )
    embedder = FakeEmbedder()

    _ingest(database_session, [source], embedder, config)
    database_session.flush()

    assert embedder.calls == 1
    assert [document.version for document in _documents(
        database_session, source.document_key
    )] == [1, 2]


def test_embedding_dimension_change_triggers_reembedding(database_session):
    source = _source("Embedding dimension content.")
    _ingest(database_session, [source], FakeEmbedder(), _config())
    database_session.flush()
    changed_config = _config(dimension=384)
    embedder = DimensionEmbedder(384)

    _ingest(database_session, [source], embedder, changed_config)
    database_session.flush()

    documents = _documents(database_session, source.document_key)
    assert embedder.calls == 1
    assert [document.version for document in documents] == [1, 2]
    assert documents[1].embedding_dimension == 384


def test_cli_main_idempotency_skips_gemini_and_duplicate_versions(
    database_engine,
    monkeypatch,
):
    session_local = sessionmaker(
        bind=database_engine,
        autoflush=False,
        expire_on_commit=False,
    )
    embedder = FakeEmbedder()
    monkeypatch.setattr(ingest_knowledge, "get_session_local", lambda: session_local)
    monkeypatch.setattr(
        ingest_knowledge,
        "create_configured_embedder",
        lambda: embedder,
    )

    assert ingest_knowledge.main() == 0
    first_call_count = embedder.calls
    assert first_call_count > 0

    assert ingest_knowledge.main() == 0

    with Session(database_engine) as session:
        documents = session.scalars(
            select(KnowledgeDocument).order_by(KnowledgeDocument.document_key)
        ).all()
        assert len(documents) == 5
        assert all(document.version == 1 for document in documents)
        assert embedder.calls == first_call_count


def test_batch_keeps_one_active_version_and_historical_versions(database_session):
    sources = [_source("Version one.", key="policy-a"), _source("Version one.", key="policy-b")]
    _ingest(database_session, sources, FakeEmbedder(), _config())
    database_session.flush()
    replacements = [
        _source("Version two.", key="policy-a"),
        _source("Version two.", key="policy-b"),
    ]

    _ingest(database_session, replacements, FakeEmbedder(), _config())
    database_session.flush()

    for source in sources:
        documents = _documents(database_session, source.document_key)
        assert [document.version for document in documents] == [1, 2]
        assert sum(document.is_active for document in documents) == 1


def test_invalid_embedding_fails_before_database_persistence(database_session):
    source = _source("Invalid vector content.")

    with pytest.raises(EmbeddingError):
        prepared = prepare_documents([source], InvalidEmbedder(), _config())
        persist_prepared_documents(database_session, prepared, _config())

    assert database_session.scalars(select(KnowledgeDocument)).all() == []


def test_embedding_failure_before_database_persistence(database_session):
    sources = [_source("First content."), _source("Second content.")]

    with pytest.raises(EmbeddingError):
        prepared = prepare_documents(sources, FailingEmbedder(), _config())
        persist_prepared_documents(database_session, prepared, _config())

    assert database_session.scalars(select(KnowledgeDocument)).all() == []


def test_mid_batch_failure_rolls_back_all_five_documents(
    database_engine,
):
    from sqlalchemy.orm import Session

    keys = [f"policy-{index}" for index in range(5)]
    sources = [_source("Original content.", key=key) for key in keys]
    with Session(database_engine) as seed_session:
        with seed_session.begin():
            _ingest(seed_session, sources, FakeEmbedder(), _config())
    with Session(database_engine) as verification_session:
        original_ids = {
            document.document_key: document.id
            for document in verification_session.scalars(
                select(KnowledgeDocument)
            ).all()
        }

    replacements = [
        _source("Replacement content.", key=key) for key in keys
    ]
    prepared = prepare_documents(replacements, FakeEmbedder(), _config())

    with Session(database_engine) as batch_session:
        original_flush = batch_session.flush
        flush_count = 0

        def fail_on_second_replacement(*args, **kwargs):
            nonlocal flush_count
            flush_count += 1
            if flush_count == 3:
                raise RuntimeError("synthetic database failure")
            return original_flush(*args, **kwargs)

        batch_session.flush = fail_on_second_replacement
        with pytest.raises(RuntimeError, match="synthetic database failure"):
            with batch_session.begin():
                persist_prepared_documents(
                    batch_session,
                    prepared,
                    _config(),
                )

    with Session(database_engine) as verification_session:
        documents = verification_session.scalars(
            select(KnowledgeDocument).order_by(KnowledgeDocument.document_key)
        ).all()
        active = [
            document for document in documents if document.is_active
        ]
        assert {document.document_key: document.id for document in active} == original_ids
        assert len(documents) == 5
        assert all(document.version == 1 for document in documents)
        assert all(
            document.content.startswith("Original")
            for document in documents
        )
        assert verification_session.scalars(select(DocumentChunk)).all()


def test_database_failure_rolls_back_document_replacement(database_session):
    source = _source("The active policy version.")
    working = _ingest(database_session, [source], FakeEmbedder(), _config())[0]
    database_session.flush()
    replacement = _source(
        "The replacement policy version.",
        key=source.document_key,
    )
    prepared = prepare_documents([replacement], FakeEmbedder(), _config())

    with pytest.raises(RuntimeError, match="synthetic database failure"):
        original_flush = database_session.flush
        flush_count = 0

        def fail_on_replacement_flush(*args, **kwargs):
            nonlocal flush_count
            flush_count += 1
            if flush_count == 2:
                raise RuntimeError("synthetic database failure")
            return original_flush(*args, **kwargs)

        database_session.flush = fail_on_replacement_flush
        with database_session.begin_nested():
            persist_prepared_documents(database_session, prepared, _config())

    documents = database_session.scalars(
        select(KnowledgeDocument).where(
            KnowledgeDocument.document_key == source.document_key
        )
    ).all()
    assert len(documents) == 1
    assert documents[0].id == working.id
    assert documents[0].is_active is True
