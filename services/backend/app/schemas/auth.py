from typing import Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    model_validator,
)

from .session import SessionResponse


class AuthChallengeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(strict=True, ge=1, le=1)
    challenge_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    device_id: str = Field(min_length=1)
    purpose: Literal["login", "reauthentication"]
    nonce: str = Field(min_length=1)
    expires_at: AwareDatetime


class DeviceResponsePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    purpose: Literal["login", "reauthentication"]
    nonce: str = Field(min_length=1)
    verified: StrictBool


class AuthVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(strict=True, ge=1, le=1)
    challenge_id: str = Field(min_length=1)
    device_id: str = Field(min_length=1)
    payload: DeviceResponsePayload
    signature: str = Field(min_length=1)


class AuthChallengeCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=1, max_length=36)
    device_id: str = Field(min_length=1, max_length=36)
    purpose: Literal["login", "reauthentication"]
    session_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=36,
    )

    @model_validator(mode="after")
    def validate_session_context(self):
        if self.purpose == "login" and self.session_id is not None:
            raise ValueError("Login must not include session_id.")

        if self.purpose == "reauthentication" and self.session_id is None:
            raise ValueError("Reauthentication requires session_id.")

        return self


class AuthChallengeCreateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    challenge: AuthChallengeResponse


class AuthVerifyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session: SessionResponse