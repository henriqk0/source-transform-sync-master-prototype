"""T039 — PATCH /api/professors/{id} contract (owner/ADMIN, 403 cross)."""

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
    provider.researchers.add(Researcher(id=2, name="Other"))
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


def test_patch_200_owner_updates_fields(session_factory, client):
    token = _token(session_factory, client.app, "maria")
    response = client.patch(
        "/api/professors/1",
        json={
            "name": "Maria Alice",
            "emails": ["maria@ifes.edu.br"],
            "resume": "Atualizado.",
        },
        headers=_auth(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "id": 1,
        "name": "Maria Alice",
        "emails": ["maria@ifes.edu.br"],
        "resume": "Atualizado.",
    }


def test_patch_200_admin_on_any_professor(session_factory, client):
    token = _token(session_factory, client.app, "admin")
    response = client.patch(
        "/api/professors/2",
        json={"name": "Renomeado"},
        headers=_auth(token),
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Renomeado"


def test_patch_403_cross_professor_denied_fr018(session_factory, client):
    token = _token(session_factory, client.app, "maria")
    response = client.patch(
        "/api/professors/2",
        json={"name": "Nao devia mudar"},
        headers=_auth(token),
    )
    assert response.status_code == 403


def test_patch_401_anonymous(client):
    response = client.patch("/api/professors/1", json={"name": "X"})
    assert response.status_code == 401


def test_patch_404_unknown_professor(session_factory, client):
    token = _token(session_factory, client.app, "maria")
    response = client.patch(
        "/api/professors/999", json={"name": "X"}, headers=_auth(token)
    )
    assert response.status_code == 404


def test_patch_422_invalid_emails_type(session_factory, client):
    token = _token(session_factory, client.app, "maria")
    response = client.patch(
        "/api/professors/1",
        json={"emails": "not-a-list"},
        headers=_auth(token),
    )
    assert response.status_code == 422


def test_patch_owner_email_persisted_across_requests(session_factory, client):
    token = _token(session_factory, client.app, "maria")
    client.patch(
        "/api/professors/1",
        json={"emails": ["nova@ifes.edu.br"]},
        headers=_auth(token),
    )
    again = client.patch("/api/professors/1", json={}, headers=_auth(token))
    assert again.json()["emails"] == ["nova@ifes.edu.br"]
