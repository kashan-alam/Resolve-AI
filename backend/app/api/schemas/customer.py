import uuid

from pydantic import BaseModel, ConfigDict


class CustomerSummary(BaseModel):
    model_config = ConfigDict(strict=True)

    id: uuid.UUID
    name: str
    email: str
