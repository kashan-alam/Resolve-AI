import logging
from types import SimpleNamespace

import pytest
from google.genai import types

from backend.app.ai.generation import GenerationError, GenerationService
from backend.app.ai.schemas import GroundedResponseDraft


class FakeModels:
    def __init__(self, response=None, error=None) -> None:
        self.response = response
        self.error = error
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


class FakeClient:
    def __init__(self, models) -> None:
        self.models = models


def _response(parts, finish_reason="STOP"):
    return SimpleNamespace(
        candidates=[
            SimpleNamespace(
                finish_reason=finish_reason,
                content=SimpleNamespace(parts=parts),
            )
        ]
    )


def test_structured_generation_disables_function_calling() -> None:
    models = FakeModels(_response([SimpleNamespace(text='{"message":"ok"}')]))
    service = GenerationService("key", client=FakeClient(models))

    result = service.generate_structured("prompt", GroundedResponseDraft)

    assert result.message == "ok"
    config = models.calls[0]["config"]
    assert config.tool_config.function_calling_config.mode == (
        types.FunctionCallingConfigMode.NONE
    )


def test_grounded_generation_uses_structured_output() -> None:
    models = FakeModels(_response([SimpleNamespace(text='{"message":"ok"}')]))
    service = GenerationService("key", client=FakeClient(models))

    result = service.generate_grounded_response("prompt")

    assert result.message == "ok"
    assert models.calls[0]["config"].response_mime_type == "application/json"


def test_tool_generation_uses_any_and_allowed_names() -> None:
    call = types.FunctionCall(name="demo_lookup", args={"identifier": "x"})
    models = FakeModels(_response([SimpleNamespace(function_call=call)]))
    service = GenerationService("key", client=FakeClient(models))
    declaration = types.FunctionDeclaration(name="demo_lookup", description="demo")

    result = service.generate_tool_request("prompt", [declaration])

    assert result.name == "demo_lookup"
    config = models.calls[0]["config"]
    function_config = config.tool_config.function_calling_config
    assert function_config.mode == types.FunctionCallingConfigMode.ANY
    assert function_config.allowed_function_names == ["demo_lookup"]


def test_invalid_tool_response_is_rejected() -> None:
    models = FakeModels(_response([SimpleNamespace(text="not a call")]))
    service = GenerationService("key", client=FakeClient(models))
    declaration = types.FunctionDeclaration(name="demo_lookup", description="demo")

    with pytest.raises(GenerationError):
        service.generate_tool_request("prompt", [declaration])


def test_transient_failure_is_retried_once() -> None:
    models = FakeModels(error=TimeoutError("temporary"))
    service = GenerationService("key", client=FakeClient(models))

    with pytest.raises(GenerationError):
        service.generate_structured("prompt", GroundedResponseDraft)

    assert len(models.calls) == 2


def test_gemini_failure_logs_safe_provider_metadata_and_preserves_cause(
    caplog: pytest.LogCaptureFixture,
) -> None:
    class ProviderError(Exception):
        status_code = 429
        code = "rate_limit"
        message = "provider detail " + ("x" * 600)

    error = ProviderError("do not log this message")
    models = FakeModels(error=error)
    service = GenerationService("key", client=FakeClient(models))

    with caplog.at_level(logging.WARNING, logger="backend.app.ai.generation"):
        with pytest.raises(GenerationError) as caught:
            service.generate_structured("private customer prompt", GroundedResponseDraft)

    assert caught.value.__cause__ is error
    assert "ProviderError" in caplog.text
    assert "status_code=429" in caplog.text
    assert "provider_code=rate_limit" in caplog.text
    assert "provider_message=provider detail " in caplog.text
    assert ("provider detail " + ("x" * 600)) not in caplog.text
    assert len(caplog.text.split("provider_message=", 1)[1].splitlines()[0]) < 520
    assert "do not log this message" not in caplog.text
    assert "private customer prompt" not in caplog.text
