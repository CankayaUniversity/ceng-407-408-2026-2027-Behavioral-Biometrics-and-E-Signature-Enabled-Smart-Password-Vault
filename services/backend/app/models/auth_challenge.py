from datetime import datetime
from uuid import uuid4

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database.base import Base
from ..database.types import UTCDateTime


class AuthChallenge(Base):
    __tablename__ = "auth_challenges"

    challenge_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.user_id"),
        index=True,
    )
    device_id: Mapped[str] = mapped_column(
        ForeignKey("devices.device_id"),
        index=True,
    )
    session_id: Mapped[str] = mapped_column(
        ForeignKey("sessions.session_id"),
        index=True,
    )
    purpose: Mapped[str] = mapped_column(String(30))
    expires_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
    )
    consumed_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime(),
        nullable=True,
    )
