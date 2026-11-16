from google.genai import types
import pytest

from backend.app.tools.registry import ToolDefinition, ToolRegistry
from backend.app.tools.schemas import OrderLookupArguments, ToolResult
from backend.app.tools.validation import dispatch_function_call


def _registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="demo_lookup",
            description="Controlled demo lookup.",
            arguments_model=OrderLookupArguments,
            handler=lambda args: ToolResult(data={"order_number": args.order_number}),
        )
    )
    return registry


def test_registry_dispatches_only_registered_tools() -> None:
    result = dispatch_function_call(
        types.FunctionCall(name="demo_lookup", args={"order_number": "SE1025"}),
        _registry(),
    )

    assert result.data == {"order_number": "SE1025"}


def test_registry_rejects_unknown_tools_and_arguments() -> None:
    registry = _registry()

    with pytest.raises(ValueError):
        registry.dispatch("unknown", {})
    with pytest.raises(ValueError):
        registry.dispatch("demo_lookup", {"sql": "SELECT 1"})
