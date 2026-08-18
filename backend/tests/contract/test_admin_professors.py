"""T038 — POST /api/admin/professors contract (201/400/401/403/422)."""

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
    _add_account(session_factory, "admin", Role.ADMIN)
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


def _payload(**overrides) -> dict:
    payload = {
        "name": "Joao da Silva",
        "emails": ["joao@ifes.edu.br", "joao@example.com"],
        "resume": "Professor de informatica.",
        "username": "joao",
        "password": "joao-secret",
    }
    payload.update(overrides)
    return payload


def test_register_201_creates_professor_and_account(session_factory, client):
    token = _token(session_factory, client.app, "admin")
    response = client.post(
        "/api/admin/professors", json=_payload(), headers=_auth(token)
    )
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "joao"
    assert body["role"] == "PROFESSOR"
    assert isinstance(body["researcher_id"], int)
    assert isinstance(body["id"], int)

    provider = RepositoryProvider(session_factory)
    researcher = provider.researchers.get_by_id(body["researcher_id"])
    assert researcher is not None
    assert researcher.name == "Joao da Silva"
    assert researcher.resume == "Professor de informatica."

    account = AuthRepository(session_factory).get_by_username("joao")
    assert account is not None
    assert account.role == Role.PROFESSOR
    assert account.researcher_id == body["researcher_id"]


def test_registered_account_can_log_in(session_factory, client):
    token = _token(session_factory, client.app, "admin")
    client.post("/api/admin/professors", json=_payload(), headers=_auth(token))
    login = client.post(
        "/api/auth/login",
        data={"username": "joao", "password": "joao-secret"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    assert login.json()["role"] == "PROFESSOR"


def test_register_400_duplicate_username(session_factory, client):
    token = _token(session_factory, client.app, "admin")
    first = client.post("/api/admin/professors", json=_payload(), headers=_auth(token))
    assert first.status_code == 201
    second = client.post("/api/admin/professors", json=_payload(), headers=_auth(token))
    assert second.status_code == 400


def test_register_401_unauthenticated(client):
    response = client.post("/api/admin/professors", json=_payload())
    assert response.status_code == 401


def test_register_403_non_admin_denied(session_factory, professor_client):
    token = _token(session_factory, professor_client.app, "maria")
    response = professor_client.post(
        "/api/admin/professors", json=_payload(), headers=_auth(token)
    )
    assert response.status_code == 403


def test_register_422_short_password(client):
    token = _token(client.app.state.session_factory, client.app, "admin")
    response = client.post(
        "/api/admin/professors",
        json=_payload(password="short"),
        headers=_auth(token),
    )
    assert response.status_code == 422
