"""T030 — GET /api/admin/sync-status contract (shapes, masked errors, 403)."""

from __future__ import annotations

import os
import shutil

import bcrypt
import pyarrow
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
    _add_account(session_factory, "admin", Role.ADMIN, None)
    return TestClient(app)


@pytest.fixture
def professor_client(session_factory, app) -> TestClient:
    RepositoryProvider(session_factory).researchers.add(Researcher(name="Maria"))
    _add_account(session_factory, "maria", Role.PROFESSOR, 1)
    return TestClient(app)


def _auth(session_factory, app, username: str) -> dict[str, str]:
    service = AuthService(session_factory, jwt_secret=app.state.settings.jwt_secret)
    user = service.authenticate(username, "secret123")
    assert user is not None
    return {"Authorization": f"Bearer {service.create_token(user)}"}


def test_sync_status_401_unauthenticated(client):
    assert client.get("/api/admin/sync-status").status_code == 401


def test_sync_status_403_professor_denied(session_factory, professor_client):
    response = professor_client.get(
        "/api/admin/sync-status",
        headers=_auth(session_factory, professor_client.app, "maria"),
    )
    assert response.status_code == 403


def test_sync_status_idle_shape(session_factory, client):
    response = client.get(
        "/api/admin/sync-status", headers=_auth(session_factory, client.app, "admin")
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "IDLE"
    assert body["started_at"] is None
    assert body["finished_at"] is None
    assert body["counts"] is None
    assert body["errors"] is None


def test_sync_status_running_shape(session_factory, client):
    SyncStateRepository(session_factory).begin()
    response = client.get(
        "/api/admin/sync-status", headers=_auth(session_factory, client.app, "admin")
    )
    body = response.json()
    assert body["status"] == "RUNNING"
    assert body["started_at"] is not None
    assert body["counts"] is None


def test_sync_status_succeeded_with_counts(session_factory, client):
    IngestionService(session_factory, data_dir=FIXTURES).seed()
    response = client.get(
        "/api/admin/sync-status", headers=_auth(session_factory, client.app, "admin")
    )
    body = response.json()
    assert body["status"] == "SUCCEEDED"
    assert body["finished_at"] is not None
    assert body["counts"]["researchers"] == 2
    assert body["counts"]["articles"] == 2
    assert body["errors"] == [
        {
            "file": "initiatives_canonical.parquet",
            "record": "11",
            "detail": "team references unknown person 999",
        }
    ]


def test_sync_status_failed_with_masked_errors(session_factory, client, tmp_path):
    target = tmp_path / "broken"
    shutil.copytree(FIXTURES, target)
    (target / "articles_canonical.parquet").write_bytes(b"not parquet")
    with pytest.raises(pyarrow.lib.ArrowInvalid):
        IngestionService(session_factory, data_dir=str(target)).seed()

    response = client.get(
        "/api/admin/sync-status", headers=_auth(session_factory, client.app, "admin")
    )
    body = response.json()
    assert body["status"] == "FAILED"
    assert body["errors"] is not None
    for error in body["errors"]:
        assert "email" not in error["detail"].lower()
        assert "lgpd-" not in error["detail"].lower()
        assert {"file", "record", "detail"} <= set(error.keys())
