from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database.base import Base


class SecurityEvent(Base):
    __tablename__ = "security_events"

    event_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    session_id: Mapped[str | None] = mapped_column(
        ForeignKey("sessions.session_id"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(100))
    severity: Mapped[str] = mapped_column(String(30))
    source: Mapped[str] = mapped_column(String(50))
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    sanitized_metadata: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
    )