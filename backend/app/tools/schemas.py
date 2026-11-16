from pydantic import BaseModel, ConfigDict, Field


class OrderLookupArguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    order_number: str = Field(min_length=1, max_length=32)


class ToolResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    data: dict[str, object]
