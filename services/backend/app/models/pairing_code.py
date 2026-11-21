from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database.base import Base
from ..database.types import UTCDateTime


class PairingCode(Base):
    __tablename__ = "pairing_codes"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.user_id"),
        primary_key=True,
    )
    code_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime())