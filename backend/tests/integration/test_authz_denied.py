"""T040 — authz denied cases end-to-end (no data change on denial)."""

from __future__ import annotations

import bcrypt
import pytest
from fastapi.testclient import TestClient
from research_domain.domain.entities import Researcher

from portal.auth.models import Role, UserAccount
from portal.auth.repositories import AuthRepository
from portal.auth.services import AuthService
from portal.researchdata.repositories import RepositoryProvider


def _add_account(session_factory, username: str, role: Role, researcher_id=None):
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
    provider = RepositoryProvider(session_factory)
    provider.researchers.add(Researcher(id=1, name="Maria"))
    provider.researchers.add(Researcher(id=2, name="Outro"))
    _add_account(session_factory, "maria", Role.PROFESSOR, 1)
    _add_account(session_factory, "admin", Role.ADMIN)
    return TestClient(app)


def _token(session_factory, app, username: str) -> str:
    service = AuthService(session_factory, jwt_secret=app.state.settings.jwt_secret)
    user = service.authenticate(username, "secret123")
    assert user is not None
    return service.create_token(user)


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_non_admin_registration_rejected_with_no_data_change(session_factory, client):
    provider = RepositoryProvider(session_factory)
    before_researchers = len(provider.researchers.get_all())
    before_accounts = len(AuthRepository(session_factory).get_all())

    token = _token(session_factory, client.app, "maria")
    response = client.post(
        "/api/admin/professors",
        json={
            "name": "Hacker",
            "username": "hacker",
            "password": "hacker-pass",
        },
        headers=_auth(token),
    )
    assert response.status_code == 403

    assert len(provider.researchers.get_all()) == before_researchers
    assert len(AuthRepository(session_factory).get_all()) == before_accounts


def test_cross_professor_edit_rejected_with_no_data_change(session_factory, client):
    provider = RepositoryProvider(session_factory)
    other = provider.researchers.get_by_id(2)
    assert other is not None
    original_name = other.name

    token = _token(session_factory, client.app, "maria")
    response = client.patch(
        "/api/professors/2",
        json={"name": "Alterado indevidamente"},
        headers=_auth(token),
    )
    assert response.status_code == 403

    after = provider.researchers.get_by_id(2)
    assert after.name == original_name


def test_anonymous_registration_rejected(client):
    response = client.post(
        "/api/admin/professors",
        json={"name": "Anon", "username": "anon", "password": "anon-pass"},
    )
    assert response.status_code == 401


def test_anonymous_edit_rejected(client):
    response = client.patch("/api/professors/1", json={"name": "X"})
    assert response.status_code == 401
