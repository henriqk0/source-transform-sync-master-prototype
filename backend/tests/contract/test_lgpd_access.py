"""T047 — GET /api/professors/{id}/personal-data contract (LGPD access)."""

from __future__ import annotations

import bcrypt
import pytest
from fastapi.testclient import TestClient
from research_domain.domain.entities import Campus, Researcher, University

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
    provider.universities.add(University(id=1, name="IFES"))
    provider.campuses.add(Campus(id=1, name="Vila Velha", organization_id=1))
    provider.researcher_campuses.upsert(1, 1)
    provider.researcher_emails.set_emails(1, ["maria@ifes.edu.br"])
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


def test_access_200_owner_returns_personal_data(session_factory, client):
    token = _token(session_factory, client.app, "maria")
    response = client.get("/api/professors/1/personal-data", headers=_auth(token))
    assert response.status_code == 200
    body = response.json()
    assert body["researcher_id"] == 1
    assert body["name"] == "Maria"
    assert body["emails"] == ["maria@ifes.edu.br"]
    assert isinstance(body["sensitive_fields"], list)


def test_access_200_admin_on_any_professor(session_factory, client):
    token = _token(session_factory, client.app, "admin")
    response = client.get("/api/professors/2/personal-data", headers=_auth(token))
    assert response.status_code == 200
    assert response.json()["name"] == "Outro"


def test_access_403_cross_professor_denied(session_factory, client):
    token = _token(session_factory, client.app, "maria")
    response = client.get("/api/professors/2/personal-data", headers=_auth(token))
    assert response.status_code == 403


def test_access_401_anonymous(client):
    response = client.get("/api/professors/1/personal-data")
    assert response.status_code == 401


def test_access_404_unknown_professor(session_factory, client):
    token = _token(session_factory, client.app, "admin")
    response = client.get("/api/professors/999/personal-data", headers=_auth(token))
    assert response.status_code == 404


def test_access_is_audited_without_sensitive_values(session_factory, client):
    token = _token(session_factory, client.app, "maria")
    client.get("/api/professors/1/personal-data", headers=_auth(token))
    session = session_factory()
    try:
        rows = session.execute(
            __import__("sqlalchemy").text(
                "SELECT actor_id, action, target_id, detail FROM audit_log"
            )
        ).fetchall()
    finally:
        session.close()
    assert len(rows) >= 1
    for _, action, target_id, detail in rows:
        assert action == "personal_data_access"
        assert target_id == 1
        assert "maria@ifes.edu.br" not in (detail or "")
        assert "LGPD-" not in (detail or "")
