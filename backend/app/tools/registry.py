from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from google.genai import types
from pydantic import BaseModel

from backend.app.tools.schemas import ToolResult


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    arguments_model: type[BaseModel]
    handler: Callable[[BaseModel], ToolResult]

    def declaration(self) -> types.FunctionDeclaration:
        return types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters_json_schema=self.arguments_model.model_json_schema(),
        )


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, definition: ToolDefinition) -> None:
        self._tools[definition.name] = definition

    def available(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    def declarations(self) -> list[types.FunctionDeclaration]:
        return [tool.declaration() for tool in self.available()]

    def dispatch(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        definition = self._tools.get(name)
        if definition is None:
            raise ValueError("Tool is not registered.")
        parsed = definition.arguments_model.model_validate(arguments)
        return definition.handler(parsed)
