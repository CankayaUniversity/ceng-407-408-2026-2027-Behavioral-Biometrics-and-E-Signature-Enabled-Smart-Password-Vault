from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database.base import Base
from ..database.types import UTCDateTime


class Session(Base):
    __tablename__ = "sessions"

    session_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.user_id"),
        index=True,
    )
    state: Mapped[str] = mapped_column(
        String(30),
        default="LOCKED",
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=lambda: datetime.now(timezone.utc),
    )
    expires_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
    )
    access_token_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime(),
        nullable=True,
    )
    last_reauth_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime(),
        nullable=True,
    )
