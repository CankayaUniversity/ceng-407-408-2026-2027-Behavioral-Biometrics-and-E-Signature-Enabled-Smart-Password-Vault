from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database.base import Base
from ..database.types import UTCDateTime


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    display_name: Mapped[str] = mapped_column(String(100))
    enrollment_status: Mapped[str] = mapped_column(
        String(30),
        default="PENDING",
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=lambda: datetime.now(timezone.utc),
    )

    devices: Mapped[list["Device"]] = relationship(
        "Device",
        back_populates="user",
    )
