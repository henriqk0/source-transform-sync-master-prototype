"""T054 — sync freshness integration: status reflects seed; 409 on re-sync."""

from __future__ import annotations

import os
import time

import bcrypt
import pytest
from fastapi.testclient import TestClient

from portal.auth.models import Role, UserAccount
from portal.auth.repositories import AuthRepository
from portal.auth.services import AuthService
from portal.ingestion.repositories import SyncStateRepository
from portal.researchdata.repositories import RepositoryProvider

FIXTURES = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "fixtures", "seed"
)


@pytest.fixture
def client(session_factory, app) -> TestClient:
    AuthRepository(session_factory).add(
        UserAccount(
            username="admin",
            password_hash=bcrypt.hashpw(b"secret123", bcrypt.gensalt()).decode(),
            role=Role.ADMIN,
        )
    )
    return TestClient(app)


def _token(session_factory, app) -> str:
    service = AuthService(session_factory, jwt_secret=app.state.settings.jwt_secret)
    user = service.authenticate("admin", "secret123")
    assert user is not None
    return service.create_token(user)


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _wait_succeeded(session_factory, timeout: float = 10.0) -> None:
    repo = SyncStateRepository(session_factory)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = repo.get()
        if state is not None and state.status.value == "SUCCEEDED":
            return
        time.sleep(0.05)
    raise AssertionError("seed job did not reach SUCCEEDED in time")


def test_sync_status_reflects_last_seed(session_factory, client):
    from portal.ingestion.services import IngestionService

    token = _token(session_factory, client.app)
    IngestionService(session_factory, data_dir=FIXTURES).seed()

    response = client.get("/api/admin/sync-status", headers=_auth(token))
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "SUCCEEDED"
    assert body["finished_at"] is not None
    assert body["started_at"] is not None
    assert body["counts"]["researchers"] == 2
    assert body["counts"]["articles"] == 2


def test_resync_refused_with_409_and_no_data_change(session_factory, client):
    from portal.ingestion.services import IngestionService

    token = _token(session_factory, client.app)
    IngestionService(session_factory, data_dir=FIXTURES).seed()
    provider = RepositoryProvider(session_factory)
    before = len(provider.researchers.get_all())

    response = client.post("/api/admin/seed", headers=_auth(token))
    assert response.status_code == 409
    assert response.json()["detail"] == "Database already seeded"

    assert len(provider.researchers.get_all()) == before
    status = client.get("/api/admin/sync-status", headers=_auth(token)).json()
    assert status["status"] == "SUCCEEDED"
    assert status["counts"]["researchers"] == 2


def test_api_seed_job_updates_freshness_state(session_factory, client):
    token = _token(session_factory, client.app)
    response = client.post("/api/admin/seed", headers=_auth(token))
    assert response.status_code == 202
    _wait_succeeded(session_factory)

    body = client.get("/api/admin/sync-status", headers=_auth(token)).json()
    assert body["status"] == "SUCCEEDED"
    assert body["finished_at"] is not None
    assert body["counts"]["researchers"] == 2
