from google.genai import types

from backend.app.tools.registry import ToolRegistry
from backend.app.tools.schemas import ToolResult


def dispatch_function_call(
    function_call: types.FunctionCall, registry: ToolRegistry
) -> ToolResult:
    if not function_call.name:
        raise ValueError("Tool request has no name.")
    arguments = function_call.args or {}
    if not isinstance(arguments, dict):
        raise ValueError("Tool request arguments must be an object.")
    return registry.dispatch(function_call.name, arguments)
