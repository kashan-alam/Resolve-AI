import uuid

import pytest
from sqlalchemy.orm import Session

from backend.app.models.document_chunk import DocumentChunk
from backend.app.models.knowledge_document import KnowledgeDocument
from backend.app.rag.retriever import retrieve


def test_exact_cosine_retrieval_returns_active_source(database_session: Session) -> None:
    if database_session.bind.dialect.name != "postgresql":
        pytest.skip("Exact pgvector retrieval requires PostgreSQL.")

    document = KnowledgeDocument(
        document_key=f"retrieval-test-{uuid.uuid4()}",
        title="Retrieval test",
        filename="retrieval.md",
        category="test",
        content="retrieval content",
        content_hash="a" * 64,
        version=1,
        embedding_model="gemini-embedding-001",
        embedding_dimension=768,
        embedding_configuration={"output_dimensionality": 768},
        is_active=True,
    )
    database_session.add(document)
    database_session.flush()
    database_session.add(
        DocumentChunk(
            document_id=document.id,
            chunk_index=0,
            chunk_text="Relevant evidence.",
            chunk_metadata={"document_key": document.document_key},
            embedding=[1.0] + [0.0] * 767,
        )
    )
    database_session.flush()

    result = retrieve(
        database_session,
        [1.0] + [0.0] * 767,
        dimension=768,
        top_k=1,
    )

    assert result.classification == "sufficient"
    assert result.chunks[0]["document_title"] == "Retrieval test"
    assert result.chunks[0]["chunk_text"] == "Relevant evidence."
