"""T029 — POST /api/admin/seed contract (202/409/400/401/403)."""

from __future__ import annotations

import os
import time

import bcrypt
import pytest
from fastapi.testclient import TestClient
from research_domain.domain.entities import Researcher

from portal.auth.models import Role, UserAccount
from portal.auth.repositories import AuthRepository
from portal.auth.services import AuthService
from portal.ingestion.repositories import SyncStateRepository
from portal.ingestion.services import IngestionService
from portal.researchdata.repositories import RepositoryProvider

FIXTURES = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "fixtures", "seed"
)


def _add_account(
    session_factory, username: str, role: Role, researcher_id: int | None
) -> None:
    AuthRepository(session_factory).add(
        UserAccount(
            username=username,
            password_hash=bcrypt.hashpw(b"secret123", bcrypt.gensalt()).decode(),
            role=role,
            researcher_id=researcher_id,
        )
    )


@pytest.fixture
def client(session_factory, app) -> TestClient:
    """Admin account only — database stays empty (seed allowed)."""
    _add_account(session_factory, "admin", Role.ADMIN, None)
    return TestClient(app)


@pytest.fixture
def professor_client(session_factory, app) -> TestClient:
    RepositoryProvider(session_factory).researchers.add(Researcher(name="Maria"))
    _add_account(session_factory, "maria", Role.PROFESSOR, 1)
    return TestClient(app)


def _token(session_factory, app, username: str) -> str:
    service = AuthService(session_factory, jwt_secret=app.state.settings.jwt_secret)
    user = service.authenticate(username, "secret123")
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


def test_seed_202_starts_job_and_completes(session_factory, client):
    token = _token(session_factory, client.app, "admin")
    response = client.post("/api/admin/seed", headers=_auth(token))
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "RUNNING"
    assert body["started_at"] is not None

    _wait_succeeded(session_factory)
    provider = RepositoryProvider(session_factory)
    assert len(provider.researchers.get_all()) == 2


def test_seed_409_when_database_not_empty(session_factory, client):
    token = _token(session_factory, client.app, "admin")
    IngestionService(session_factory, data_dir=FIXTURES).seed()
    response = client.post("/api/admin/seed", headers=_auth(token))
    assert response.status_code == 409
    assert response.json()["detail"] == "Database already seeded"


def test_seed_400_when_run_in_progress(session_factory, client):
    token = _token(session_factory, client.app, "admin")
    SyncStateRepository(session_factory).begin()
    response = client.post("/api/admin/seed", headers=_auth(token))
    assert response.status_code == 400
    assert response.json()["detail"] == "Seed already running"


def test_seed_401_unauthenticated(client):
    assert client.post("/api/admin/seed").status_code == 401


def test_seed_403_professor_denied(session_factory, professor_client):
    token = _token(session_factory, professor_client.app, "maria")
    response = professor_client.post("/api/admin/seed", headers=_auth(token))
    assert response.status_code == 403


def test_seed_401_invalid_token(client):
    response = client.post("/api/admin/seed", headers=_auth("not-a-valid-token"))
    assert response.status_code == 401
