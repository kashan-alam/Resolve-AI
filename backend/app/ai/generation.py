import logging
from typing import Any, TypeVar

from google.genai import types
from pydantic import BaseModel, ValidationError

from backend.app.core.config import settings
from backend.app.ai.schemas import GroundedResponseDraft


ModelT = TypeVar("ModelT", bound=BaseModel)
logger = logging.getLogger(__name__)


class GenerationError(RuntimeError):
    """Raised when Gemini cannot produce a valid controlled result."""


class GenerationService:
    def __init__(
        self,
        api_key: str,
        model: str = settings.gemini_generation_model,
        client: Any | None = None,
    ) -> None:
        if not api_key:
            raise GenerationError("GEMINI_API_KEY is required.")
        if client is None:
            from google import genai

            client = genai.Client(api_key=api_key)
        self.client = client
        self.model = model

    def _request(self, **kwargs: Any) -> Any:
        try:
            return self.client.models.generate_content(**kwargs)
        except Exception as error:
            _log_gemini_failure(error, retried=False)
            if self._is_transient(error):
                try:
                    return self.client.models.generate_content(**kwargs)
                except Exception as retry_error:
                    _log_gemini_failure(retry_error, retried=True)
                    raise GenerationError(
                        "Gemini remained unavailable after one transient retry."
                    ) from retry_error
            raise GenerationError(
                f"Gemini request failed without retry: {type(error).__name__}."
            ) from error
    @staticmethod
    def _is_transient(error: Exception) -> bool:
        if isinstance(error, (TimeoutError, ConnectionError)):
            return True
        return type(error).__name__ in {
            "ServerError",
            "ServiceUnavailableError",
        } and getattr(error, "status_code", None) in {500, 502, 503, 504}

    @staticmethod
    def _none_tool_config() -> types.ToolConfig:
        return types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(
                mode=types.FunctionCallingConfigMode.NONE
            )
        )

    def generate_structured(
        self, prompt: str, response_model: type[ModelT]
    ) -> ModelT:
        response = self._request(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=response_model.model_json_schema(),
                tool_config=self._none_tool_config(),
            ),
        )
        text = self._single_text_part(response)
        try:
            return response_model.model_validate_json(text)
        except (ValidationError, ValueError) as error:
            raise GenerationError("Gemini returned invalid structured output.") from error

    def generate_grounded_response(self, prompt: str) -> GroundedResponseDraft:
        return self.generate_structured(prompt, GroundedResponseDraft)

    def generate_tool_request(
        self, prompt: str, tool_declarations: list[types.FunctionDeclaration]
    ) -> types.FunctionCall:
        allowed_names = [declaration.name for declaration in tool_declarations]
        if not allowed_names:
            raise GenerationError("No executable tools are available.")
        response = self._request(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(function_declarations=tool_declarations)],
                tool_config=types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(
                        mode=types.FunctionCallingConfigMode.ANY,
                        allowed_function_names=allowed_names,
                    )
                ),
            ),
        )
        calls = [
            part.function_call
            for candidate in (getattr(response, "candidates", None) or [])
            for part in ((getattr(candidate, "content", None) and getattr(
                candidate.content, "parts", None
            )) or [])
            if getattr(part, "function_call", None) is not None
        ]
        if len(calls) != 1 or calls[0].name not in allowed_names:
            raise GenerationError("Gemini returned an invalid tool request.")
        return calls[0]

    def _single_text_part(self, response: Any) -> str:
        parts = [
            part
            for candidate in (getattr(response, "candidates", None) or [])
            for part in ((getattr(candidate, "content", None) and getattr(
                candidate.content, "parts", None
            )) or [])
            if getattr(part, "text", None) is not None
        ]
        if len(parts) != 1 or getattr(parts[0], "function_call", None) is not None:
            raise GenerationError("Gemini did not return exactly one text part.")
        return parts[0].text


def _log_gemini_failure(error: Exception, *, retried: bool) -> None:
    response = getattr(error, "response", None)
    status_code = getattr(error, "status_code", None)
    if status_code is None:
        status_code = getattr(response, "status_code", None)
    provider_code = getattr(error, "code", None)
    if provider_code is None:
        provider_code = getattr(error, "error_code", None)
    if provider_code is None:
        provider_code = getattr(response, "code", None)
    provider_message = getattr(error, "message", None)
    if provider_message is not None:
        provider_message = str(provider_message)[:500]

    logger.warning(
        "Gemini request failed: exception_type=%s status_code=%s "
        "provider_code=%s retried=%s provider_message=%s",
        type(error).__name__,
        status_code,
        provider_code,
        retried,
        provider_message,
    )
