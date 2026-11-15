from datetime import datetime

from pydantic import AwareDatetime, BaseModel, ConfigDict


class SessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    user_id: str
    state: str
    created_at: AwareDatetime
    expires_at: AwareDatetime
    revoked_at: datetime | None = None
    last_reauth_at: datetime | None = None