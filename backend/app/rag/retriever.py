from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.ai.embeddings import EmbeddingError, normalize_embedding
from backend.app.models.document_chunk import DocumentChunk
from backend.app.models.knowledge_document import KnowledgeDocument
from backend.app.rag.grounding import EvidenceResult, classify_evidence


def retrieve(
    session: Session,
    query_embedding: list[float],
    dimension: int = 768,
    top_k: int = 5,
    threshold: float | None = None,
) -> EvidenceResult:
    embedding = normalize_embedding(query_embedding, dimension)
    distance = DocumentChunk.embedding.cosine_distance(embedding)
    statement = (
        select(
            DocumentChunk,
            KnowledgeDocument.title,
            KnowledgeDocument.document_key,
            KnowledgeDocument.version,
            KnowledgeDocument.category,
            distance.label("distance"),
        )
        .join(KnowledgeDocument, DocumentChunk.document_id == KnowledgeDocument.id)
        .where(KnowledgeDocument.is_active.is_(True))
        .order_by(distance)
        .limit(top_k)
    )
    rows = session.execute(statement).all()
    chunks = [
        {
            "chunk_id": chunk.id,
            "document_id": chunk.document_id,
            "document_key": document_key,
            "document_title": title,
            "document_version": version,
            "category": category,
            "chunk_index": chunk.chunk_index,
            "chunk_text": chunk.chunk_text,
            "similarity": 1.0 - float(distance_value),
        }
        for chunk, title, document_key, version, category, distance_value in rows
    ]
    return classify_evidence(chunks, threshold)
