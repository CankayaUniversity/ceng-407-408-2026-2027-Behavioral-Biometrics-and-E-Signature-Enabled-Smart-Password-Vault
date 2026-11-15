from pydantic import BaseModel, ConfigDict, Field


class DevicePairRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    user_id: str = Field(min_length=1, max_length=36)
    device_id: str = Field(min_length=1, max_length=36)
    public_key: str = Field(min_length=1)


class DevicePairResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_id: str
    user_id: str
    pairing_status: str