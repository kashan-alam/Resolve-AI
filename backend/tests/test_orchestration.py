import uuid

import pytest

from backend.app.ai.orchestration import build_citations
from backend.app.ai.schemas import GroundedResponseDraft


def _chunk() -> dict[str, object]:
    return {
        "chunk_id": uuid.uuid4(),
        "document_id": uuid.uuid4(),
        "document_key": "return_policy",
        "document_title": "Return Policy",
        "document_version": 1,
        "category": "returns",
        "chunk_index": 0,
        "chunk_text": "Returns are accepted under the documented policy.",
    }


def test_citations_use_trusted_retrieval_metadata() -> None:
    chunk = _chunk()
    response = GroundedResponseDraft(
        message="The policy says this.",
        citation_chunk_ids=[str(chunk["chunk_id"])],
    )

    citations = build_citations(response.citation_chunk_ids, [chunk])

    assert citations[0].document_title == "Return Policy"
    assert citations[0].document_version == 1


def test_unknown_citation_id_is_rejected() -> None:
    response = GroundedResponseDraft(
        message="Unsupported.",
        citation_chunk_ids=[str(uuid.uuid4())],
    )

    with pytest.raises(ValueError, match="not retrieved"):
        build_citations(response.citation_chunk_ids, [_chunk()])


def test_policy_response_requires_a_retrieved_citation() -> None:
    response = GroundedResponseDraft(message="Unsupported.")

    with pytest.raises(ValueError, match="must cite"):
        from backend.app.ai.orchestration import validate_grounded_response

        validate_grounded_response(response, [_chunk()])
