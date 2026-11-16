from pydantic import BaseModel, ConfigDict, Field


class AdminLoginRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    username: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=1, max_length=512)


class AdminTokenResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    access_token: str
    token_type: str
    expires_in: int


class AdminIdentity(BaseModel):
    model_config = ConfigDict(strict=True)

    username: str
