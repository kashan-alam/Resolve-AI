import pytest
from pydantic import ValidationError

from backend.app.ai.schemas import Category, IntentExtraction, IssueType


def _extraction(**overrides: object) -> dict[str, object]:
    value = {
        "category": "Shipping",
        "issue_type": "not-a-real-type",
        "requested_action": "answer",
        "requires_policy_retrieval": True,
        "human_support_requested": False,
        "needs_clarification": False,
    }
    return {**value, **overrides}


def test_extraction_normalizes_known_values_and_maps_unknown_safely() -> None:
    result = IntentExtraction.model_validate(_extraction())

    assert result.category is Category.SHIPPING
    assert result.issue_type is IssueType.UNKNOWN


def test_extraction_rejects_unexpected_fields() -> None:
    with pytest.raises(ValidationError):
        IntentExtraction.model_validate(_extraction(unsupported_decision=True))
