import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from backend.app.ai.generation import GenerationError
from backend.app.ai.schemas import (
    Category,
    Citation,
    GroundedResponseDraft,
    IntentExtraction,
    IssueType,
    RequestedAction,
)
from backend.app.api.routers.customer import (
    create_conversation,
    list_customers,
    send_message,
)
from backend.app.api.schemas.conversation import ConversationCreate, MessageCreate
from backend.app.core.database import get_db
from backend.app.main import app
from backend.app.models.conversation import Conversation
from backend.app.models.customer import Customer
from backend.app.models.ticket import Ticket
from backend.app.rag.grounding import EvidenceResult
from backend.app.services.support_workflow import (
    SupportWorkflowError,
    _get_or_create_ticket,
    process_support_message,
)
from backend.app.tools.order_lookup import create_order_tool_registry


class FakeSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.commit_count = 0
        self.rollback_count = 0

    def add(self, value: object) -> None:
        if hasattr(value, "id") and getattr(value, "id", None) is None:
            value.id = uuid.uuid4()
        if hasattr(value, "created_at") and getattr(value, "created_at", None) is None:
            value.created_at = datetime.now(timezone.utc)
        self.added.append(value)

    def commit(self) -> None:
        self.commit_count += 1

    def refresh(self, value: object) -> None:
        if getattr(value, "created_at", None) is None:
            value.created_at = datetime.now(timezone.utc)

    def rollback(self) -> None:
        self.rollback_count += 1

    def begin(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        return None

    def flush(self) -> None:
        for value in self.added:
            if getattr(value, "id", None) is None and hasattr(value, "id"):
                value.id = uuid.uuid4()

    def scalar(self, statement):
        return None


class FakeOrchestration:
    def __init__(self, extraction: IntentExtraction) -> None:
        self.generation = object()
        self.tools = Mock()
        self.extraction = extraction

    def extract(self, prompt, response_model):
        return self.extraction

    def draft_policy_response(self, prompt, retrieved_chunks):
        citation = Citation.model_validate(retrieved_chunks[0])
        return (
            GroundedResponseDraft(
                message="The policy says this.",
                citation_chunk_ids=[str(citation.chunk_id)],
            ),
            [citation],
        )


class FakeEmbedder:
    dimension = 768

    def embed(self, text: str) -> list[float]:
        return [1.0]


def _customer_and_conversation() -> tuple[Customer, Conversation]:
    customer = Customer(id=uuid.uuid4(), name="Demo Customer", email="demo@example.com")
    conversation = Conversation(
        id=uuid.uuid4(), customer_id=customer.id, status="active"
    )
    return customer, conversation


def _policy_extraction() -> IntentExtraction:
    return IntentExtraction(
        category=Category.RETURNS,
        issue_type=IssueType.UNKNOWN,
        requested_action=RequestedAction.ANSWER,
        requires_policy_retrieval=True,
        human_support_requested=False,
        needs_clarification=False,
    )


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
        "similarity": 0.99,
    }


def test_real_order_handler_is_registered_and_customer_scoped() -> None:
    session = Mock()
    session.scalar.return_value = SimpleNamespace(
        order_number="SE1025",
        product="Demo product",
        category="electronics",
        quantity=1,
        total_amount=Decimal("25.00"),
        currency="USD",
        order_status="shipped",
        payment_status="paid",
        order_date=date(2026, 1, 1),
        shipping_date=None,
        delivery_date=None,
    )
    customer_id = uuid.uuid4()

    registry = create_order_tool_registry(session, customer_id)
    result = registry.dispatch(
        "lookup_customer_order", {"order_number": "SE1025"}
    )

    assert result.data["found"] is True
    assert result.data["order_number"] == "SE1025"
    statement = session.scalar.call_args.args[0]
    compiled = str(statement.compile(compile_kwargs={"literal_binds": True}))
    assert str(customer_id).replace("-", "") in compiled


def test_cross_customer_order_is_not_exposed() -> None:
    session = Mock()
    session.scalar.return_value = None

    result = create_order_tool_registry(
        session, uuid.uuid4()
    ).dispatch("lookup_customer_order", {"order_number": "SE1025"})

    assert result.data == {"found": False, "order_number": "SE1025"}


def test_customer_listing_and_conversation_creation() -> None:
    customer, _ = _customer_and_conversation()
    session = FakeSession()
    session.get = Mock(return_value=customer)
    session.scalars = Mock(
        return_value=SimpleNamespace(all=lambda: [customer])
    )

    customers = list_customers(session)
    conversation = create_conversation(
        ConversationCreate(customer_id=customer.id), session
    )

    assert customers[0].id == customer.id
    assert conversation.customer_id == customer.id
    assert session.commit_count == 1


def test_conversation_creation_accepts_json_uuid_and_rejects_invalid_fields() -> None:
    customer_id = uuid.uuid4()
    parsed = ConversationCreate.model_validate_json(
        f'{{"customer_id":"{customer_id}"}}'
    )
    assert parsed.customer_id == customer_id

    with pytest.raises(ValidationError):
        ConversationCreate.model_validate_json(
            '{"customer_id":"not-a-uuid"}'
        )
    with pytest.raises(ValidationError):
        ConversationCreate.model_validate_json(
            f'{{"customer_id":"{customer_id}","unexpected":"value"}}'
        )


def test_conversation_creation_api_accepts_json_uuid() -> None:
    customer, _ = _customer_and_conversation()
    session = FakeSession()
    session.get = Mock(return_value=customer)

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        from fastapi.testclient import TestClient

        response = TestClient(app).post(
            "/api/v1/conversations",
            json={"customer_id": str(customer.id)},
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 201
    assert response.json()["customer_id"] == str(customer.id)


def test_message_creation_schema_converts_uuid_and_forbids_extra_fields() -> None:
    customer_id = uuid.uuid4()
    parsed = MessageCreate.model_validate_json(
        f'{{"customer_id":"{customer_id}","content":"Hello"}}'
    )
    assert parsed.customer_id == customer_id

    with pytest.raises(ValidationError):
        MessageCreate.model_validate_json(
            '{"customer_id":"not-a-uuid","content":"Hello"}'
        )
    with pytest.raises(ValidationError):
        MessageCreate.model_validate_json(
            f'{{"customer_id":"{customer_id}","content":"Hello",'
            '"unexpected":"value"}'
        )


def test_ticket_creation_reuse_and_evidence_persistence() -> None:
    session = FakeSession()
    customer, conversation = _customer_and_conversation()
    citation = Citation.model_validate(_chunk())
    extraction = IntentExtraction(
        category=Category.OTHER,
        issue_type=IssueType.UNKNOWN,
        requested_action=RequestedAction.HUMAN_SUPPORT,
        requires_policy_retrieval=False,
        human_support_requested=True,
        needs_clarification=False,
    )

    first = _get_or_create_ticket(
        session, conversation, customer, extraction, [citation]
    )
    assert isinstance(first, Ticket)
    assert first.status == "pending_human_review"
    assert any(
        item.__class__.__name__ == "TicketPolicyEvidence"
        for item in session.added
    )

    session.scalar = Mock(return_value=first)
    second = _get_or_create_ticket(
        session, conversation, customer, extraction, []
    )
    assert second.id == first.id
    assert len([item for item in session.added if isinstance(item, Ticket)]) == 1


def test_policy_response_returns_validated_citation(monkeypatch) -> None:
    session = FakeSession()
    customer, conversation = _customer_and_conversation()
    chunk = _chunk()
    monkeypatch.setattr(
        "backend.app.services.support_workflow.retrieve",
        lambda *args, **kwargs: EvidenceResult("sufficient", (chunk,)),
    )

    result = process_support_message(
        session,
        customer,
        conversation,
        "What is the return policy?",
        FakeOrchestration(_policy_extraction()),
        FakeEmbedder(),
    )

    assert result.assistant_message.content == "The policy says this."
    assert result.citations[0].document_title == "Return Policy"
    assert result.insufficient_evidence is False
    assert session.commit_count == 1


def test_configured_retrieval_limits_are_used_for_safe_insufficient_evidence(
    monkeypatch,
) -> None:
    session = FakeSession()
    customer, conversation = _customer_and_conversation()
    captured: dict[str, object] = {}

    def fake_retrieve(*args, **kwargs):
        captured.update(kwargs)
        return EvidenceResult("insufficient", ())

    monkeypatch.setattr(
        "backend.app.services.support_workflow.retrieve", fake_retrieve
    )
    monkeypatch.setattr(
        "backend.app.services.support_workflow.settings",
        type(
            "ConfiguredSettings",
            (),
            {"rag_top_k": 2, "rag_similarity_threshold": 0.91},
        )(),
    )
    orchestration = FakeOrchestration(_policy_extraction())
    orchestration.draft_policy_response = Mock()

    result = process_support_message(
        session,
        customer,
        conversation,
        "Can I receive compensation?",
        orchestration,
        FakeEmbedder(),
    )

    assert captured["top_k"] == 2
    assert captured["threshold"] == 0.91
    assert result.insufficient_evidence is True
    orchestration.draft_policy_response.assert_not_called()


def test_insufficient_evidence_does_not_generate_policy_claim(
    monkeypatch,
) -> None:
    session = FakeSession()
    customer, conversation = _customer_and_conversation()
    orchestration = FakeOrchestration(_policy_extraction())
    orchestration.draft_policy_response = Mock()
    monkeypatch.setattr(
        "backend.app.services.support_workflow.retrieve",
        lambda *args, **kwargs: EvidenceResult("insufficient", ()),
    )

    result = process_support_message(
        session,
        customer,
        conversation,
        "Can I receive compensation?",
        orchestration,
        FakeEmbedder(),
    )

    assert result.insufficient_evidence is True
    assert "could not find enough information" in result.assistant_message.content
    orchestration.draft_policy_response.assert_not_called()


def test_ai_failure_preserves_customer_message() -> None:
    session = FakeSession()
    customer, conversation = _customer_and_conversation()
    orchestration = FakeOrchestration(_policy_extraction())
    orchestration.extract = Mock(
        side_effect=GenerationError("mocked generation failure")
    )

    with pytest.raises(SupportWorkflowError):
        process_support_message(
            session,
            customer,
            conversation,
            "What is the return policy?",
            orchestration,
            FakeEmbedder(),
        )

    customer_messages = [
        item for item in session.added if getattr(item, "sender_type", None) == "customer"
    ]
    assert len(customer_messages) == 1
    assert session.commit_count == 1
    assert session.rollback_count == 1


def test_service_construction_failure_preserves_committed_message(monkeypatch) -> None:
    session = FakeSession()
    customer, conversation = _customer_and_conversation()
    session.get = Mock(return_value=customer)
    session.scalar = Mock(return_value=conversation)
    monkeypatch.setattr(
        "backend.app.api.routers.customer.GenerationService",
        Mock(side_effect=GenerationError("mocked initialization failure")),
    )

    with pytest.raises(Exception) as caught:
        send_message(
            customer.id,
            conversation.id,
            MessageCreate(customer_id=customer.id, content="Hello"),
            session,
        )

    assert getattr(caught.value, "status_code", None) == 502
    customer_messages = [
        item
        for item in session.added
        if getattr(item, "sender_type", None) == "customer"
    ]
    assert len(customer_messages) == 1
    assert session.commit_count == 1


def test_customer_b_cannot_retrieve_customer_a_conversation() -> None:
    customer_a_id = uuid.uuid4()
    customer_b_id = uuid.uuid4()
    conversation_a_id = uuid.uuid4()
    session = Mock()
    session.scalar.return_value = None

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        from fastapi.testclient import TestClient

        response = TestClient(app).get(
            f"/api/v1/customers/{customer_b_id}/conversations/{conversation_a_id}"
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 404
    assert response.json() == {"detail": "Conversation not found."}
    assert "messages" not in response.json()


def test_conversation_detail_returns_latest_ticket_status() -> None:
    customer_id = uuid.uuid4()
    conversation_id = uuid.uuid4()
    older_ticket = SimpleNamespace(
        id=uuid.uuid4(),
        ticket_number="T-OLDER",
        status="resolved",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    latest_ticket = SimpleNamespace(
        id=uuid.uuid4(),
        ticket_number="T-LATEST",
        status="pending_human_review",
        created_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )
    conversation = SimpleNamespace(
        id=conversation_id,
        customer_id=customer_id,
        status="active",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        tickets=[older_ticket, latest_ticket],
    )
    session = Mock()
    session.scalar.return_value = conversation
    session.scalars.return_value = SimpleNamespace(all=lambda: [])

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        from fastapi.testclient import TestClient

        first_response = TestClient(app).get(
            f"/api/v1/customers/{customer_id}/conversations/{conversation_id}"
        )
        latest_ticket.status = "resolved"
        second_response = TestClient(app).get(
            f"/api/v1/customers/{customer_id}/conversations/{conversation_id}"
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert first_response.status_code == 200
    assert first_response.json()["ticket"] == {
        "ticket_number": "T-LATEST",
        "status": "pending_human_review",
    }
    assert second_response.status_code == 200
    assert second_response.json()["ticket"] == {
        "ticket_number": "T-LATEST",
        "status": "resolved",
    }
