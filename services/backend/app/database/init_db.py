from sqlalchemy import inspect, text

from .. import models
from .base import Base
from .connection import engine


def init_db() -> None:
    with engine.begin() as connection:
        Base.metadata.create_all(bind=connection)

        challenge_columns = {
            column["name"]
            for column in inspect(connection).get_columns("auth_challenges")
        }

        if "protocol_version" not in challenge_columns:
            connection.execute(
                text(
                    "ALTER TABLE auth_challenges "
                    "ADD COLUMN protocol_version INTEGER"
                )
            )

        if "request_id" not in challenge_columns:
            connection.execute(
                text(
                    "ALTER TABLE auth_challenges "
                    "ADD COLUMN request_id VARCHAR(36)"
                )
            )

        if "nonce" not in challenge_columns:
            connection.execute(
                text(
                    "ALTER TABLE auth_challenges "
                    "ADD COLUMN nonce VARCHAR(43)"
                )
            )

        session_columns = {
            column["name"]
            for column in inspect(connection).get_columns("sessions")
        }

        if "access_token_hash" not in session_columns:
            connection.execute(
                text(
                    "ALTER TABLE sessions "
                    "ADD COLUMN access_token_hash VARCHAR(64)"
                )
            )


if __name__ == "__main__":
    try:
        init_db()
        print("Database tables created.")
    finally:
        engine.dispose()