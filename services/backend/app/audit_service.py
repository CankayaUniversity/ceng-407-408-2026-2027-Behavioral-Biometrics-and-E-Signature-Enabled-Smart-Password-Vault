from sqlalchemy.orm import Session as DatabaseSession

from .models.security_event import SecurityEvent


def record_security_event(
    db: DatabaseSession,
    *,
    event_type: str,
    severity: str,
    reason_code: str,
    session_id: str | None = None,
    actor_user_id: str | None = None,
    device_id: str | None = None,
) -> None:
    metadata = {"reason_code": reason_code}

    if actor_user_id is not None:
        metadata["actor_user_id"] = actor_user_id
    if device_id is not None:
        metadata["device_id"] = device_id

    db.add(
        SecurityEvent(
            session_id=session_id,
            event_type=event_type,
            severity=severity,
            source="backend",
            sanitized_metadata=metadata,
        )
    )