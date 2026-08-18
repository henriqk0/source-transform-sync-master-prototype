"""T037 — POST /api/auth/login + GET /api/auth/me contract."""

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
    RepositoryProvider(session_factory).researchers.add(Researcher(id=7, name="Maria"))
    _add_account(session_factory, "admin", Role.ADMIN)
    _add_account(session_factory, "maria", Role.PROFESSOR, 7)
    return TestClient(app)


def _login(client: TestClient, username: str, password: str):
    return client.post(
        "/api/auth/login",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )


def test_login_200_with_valid_credentials(client):
    response = _login(client, "maria", "secret123")
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["role"] == "PROFESSOR"
    assert body["researcher_id"] == 7
    assert len(body["access_token"]) > 0


def test_login_200_admin_has_null_researcher_id(client):
    response = _login(client, "admin", "secret123")
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "ADMIN"
    assert body["researcher_id"] is None


def test_login_401_wrong_password(client):
    response = _login(client, "maria", "not-the-password")
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"


def test_login_401_unknown_user(client):
    response = _login(client, "ghost", "secret123")
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"


def test_login_422_missing_fields(client):
    response = client.post("/api/auth/login", data={"username": "maria"})
    assert response.status_code == 422


def test_me_200_with_valid_token(session_factory, client):
    service = AuthService(
        session_factory, jwt_secret=client.app.state.settings.jwt_secret
    )
    user = service.authenticate("maria", "secret123")
    token = service.create_token(user)
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == {
        "id": user.id,
        "username": "maria",
        "role": "PROFESSOR",
        "researcher_id": 7,
    }


def test_me_401_without_token(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_401_with_invalid_token(client):
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert response.status_code == 401
