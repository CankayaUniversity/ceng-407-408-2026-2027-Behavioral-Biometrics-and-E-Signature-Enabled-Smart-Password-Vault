from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserCreateRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    display_name: str = Field(min_length=1, max_length=100)


class UserCreateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    display_name: str
    enrollment_status: str
    created_at: datetime