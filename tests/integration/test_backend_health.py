import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from services.backend.app import main as backend


@pytest.fixture
def client(tmp_path, monkeypatch):
    database_path = (tmp_path / "test.db").as_posix()
    test_engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False},
    )
    monkeypatch.setattr(backend, "engine", test_engine)

    with TestClient(backend.app) as test_client:
        yield test_client


def test_health_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database": "ok",
    }


def test_health_returns_503_when_database_unavailable(client, monkeypatch):
    def fail_to_connect():
        raise OperationalError("SELECT 1", {}, Exception("Connection failed"))

    monkeypatch.setattr(backend.engine, "connect", fail_to_connect)

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}