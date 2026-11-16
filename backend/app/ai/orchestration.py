import uuid
from collections.abc import Iterable
from typing import Any

from backend.app.ai.generation import GenerationService
from backend.app.ai.schemas import Citation, GroundedResponseDraft
from backend.app.tools.registry import ToolRegistry
from backend.app.tools.schemas import ToolResult
from backend.app.tools.validation import dispatch_function_call


def build_citations(
    citation_chunk_ids: list[str], retrieved_chunks: Iterable[dict[str, Any]]
) -> list[Citation]:
    trusted = {str(chunk["chunk_id"]): chunk for chunk in retrieved_chunks}
    citations: list[Citation] = []
    for raw_id in citation_chunk_ids:
        try:
            chunk_id = uuid.UUID(raw_id)
        except (ValueError, AttributeError, TypeError) as error:
            raise ValueError("Citation ID is not a valid UUID.") from error
        chunk = trusted.get(str(chunk_id))
        if chunk is None:
            raise ValueError("Citation ID was not retrieved.")
        citations.append(Citation.model_validate(chunk))
    return citations


def validate_grounded_response(
    response: GroundedResponseDraft, retrieved_chunks: list[dict[str, Any]]
) -> list[Citation]:
    if not response.citation_chunk_ids:
        raise ValueError("A policy response must cite retrieved evidence.")
    return build_citations(response.citation_chunk_ids, retrieved_chunks)


class OrchestrationService:
    def __init__(
        self, generation: GenerationService, tools: ToolRegistry
    ) -> None:
        self.generation = generation
        self.tools = tools

    def extract(self, prompt: str, response_model: type[Any]) -> Any:
        return self.generation.generate_structured(prompt, response_model)

    def request_tool(self, prompt: str) -> ToolResult:
        function_call = self.generation.generate_tool_request(
            prompt, self.tools.declarations()
        )
        return dispatch_function_call(function_call, self.tools)

    def draft_policy_response(
        self, prompt: str, retrieved_chunks: list[dict[str, Any]]
    ) -> tuple[GroundedResponseDraft, list[Citation]]:
        response = self.generation.generate_grounded_response(prompt)
        citations = validate_grounded_response(response, retrieved_chunks)
        return response, citations
