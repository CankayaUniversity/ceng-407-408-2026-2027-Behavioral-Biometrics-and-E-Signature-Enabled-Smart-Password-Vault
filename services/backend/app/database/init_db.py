from .. import models
from .base import Base
from .connection import engine


def init_db():
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    try:
        init_db()
        print("Database tables created.")
    finally:
        engine.dispose()