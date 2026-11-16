import uuid
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Category(StrEnum):
    SHIPPING = "shipping"
    RETURNS = "returns"
    REFUNDS = "refunds"
    WARRANTY = "warranty"
    DEFECTIVE_PRODUCT = "defective_product"
    PAYMENT = "payment"
    CANCELLATION = "cancellation"
    OTHER = "other"


class IssueType(StrEnum):
    DELAYED_DELIVERY = "delayed_delivery"
    MISSING_PACKAGE = "missing_package"
    DEFECTIVE_PRODUCT = "defective_product"
    DAMAGED_PRODUCT = "damaged_product"
    INCORRECT_ITEM = "incorrect_item"
    DUPLICATE_PAYMENT = "duplicate_payment"
    REFUND_DELAY = "refund_delay"
    CANCELLATION = "cancellation"
    UNKNOWN = "unknown"


class RequestedAction(StrEnum):
    ANSWER = "answer"
    ORDER_LOOKUP = "order_lookup"
    HUMAN_SUPPORT = "human_support"
    CLARIFICATION = "clarification"
    UNKNOWN = "unknown"


def _normalized(value: object) -> str:
    return str(value).strip().lower().replace("-", "_").replace(" ", "_")


class IntentExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    category: Category
    issue_type: IssueType
    requested_action: RequestedAction
    order_number: str | None = None
    product: str | None = None
    requires_policy_retrieval: bool
    human_support_requested: bool
    needs_clarification: bool
    clarification_question: str | None = None

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, value: object) -> Category:
        normalized = _normalized(value)
        try:
            return Category(normalized)
        except ValueError:
            return Category.OTHER

    @field_validator("issue_type", mode="before")
    @classmethod
    def normalize_issue_type(cls, value: object) -> IssueType:
        normalized = _normalized(value)
        try:
            return IssueType(normalized)
        except ValueError:
            return IssueType.UNKNOWN

    @field_validator("requested_action", mode="before")
    @classmethod
    def normalize_requested_action(cls, value: object) -> RequestedAction:
        normalized = _normalized(value)
        try:
            return RequestedAction(normalized)
        except ValueError:
            return RequestedAction.UNKNOWN

    @field_validator("order_number")
    @classmethod
    def normalize_order_number(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        return normalized or None


class GroundedResponseDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    message: str = Field(min_length=1)
    citation_chunk_ids: list[str] = Field(default_factory=list)
    clarification_question: str | None = None


class ToolRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: str
    arguments: dict[str, object]


class Citation(BaseModel):
    model_config = ConfigDict(strict=True)

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_key: str
    document_title: str
    document_version: int
    category: str
    chunk_index: int
    chunk_text: str


class ToolProvenance(BaseModel):
    model_config = ConfigDict(strict=True)

    tool_name: str
    result: dict[str, object]


class OrchestrationResult(BaseModel):
    model_config = ConfigDict(strict=True)

    extraction: IntentExtraction
    message: str
    policy_citations: list[Citation] = Field(default_factory=list)
    tool_provenance: ToolProvenance | None = None
    insufficient_evidence: bool = False
