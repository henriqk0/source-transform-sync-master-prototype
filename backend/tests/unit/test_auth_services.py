"""T036 — Auth services: bcrypt hashing, JWT issuance, claims."""

from __future__ import annotations

import bcrypt
import jwt
import pytest
from research_domain.domain.entities import Researcher

from portal.auth.models import Role, UserAccount
from portal.auth.repositories import AuthRepository
from portal.auth.services import AuthService
from portal.researchdata.repositories import RepositoryProvider


@pytest.fixture
def account(session_factory) -> UserAccount:
    repository = AuthRepository(session_factory)
    RepositoryProvider(session_factory).researchers.add(Researcher(id=42, name="Maria"))
    user = UserAccount(
        username="maria",
        password_hash=bcrypt.hashpw(b"correct-horse", bcrypt.gensalt()).decode(),
        role=Role.PROFESSOR,
        researcher_id=42,
    )
    repository.add(user)
    return user


@pytest.fixture
def service(session_factory) -> AuthService:
    return AuthService(session_factory, jwt_secret="test-secret-key")


def test_authenticate_with_correct_password(service, account):
    found = service.authenticate("maria", "correct-horse")
    assert found is not None
    assert found.username == "maria"
    assert found.role == Role.PROFESSOR
    assert found.researcher_id == 42


def test_authenticate_with_wrong_password(service, account):
    assert service.authenticate("maria", "wrong-password") is None


def test_authenticate_unknown_user(service):
    assert service.authenticate("ghost", "whatever") is None


def test_create_token_contains_role_and_researcher_id_claims(service, account):
    token = service.create_token(account)
    claims = jwt.decode(token, "test-secret-key", algorithms=["HS256"])
    assert claims["sub"] == "maria"
    assert claims["role"] == "PROFESSOR"
    assert claims["researcher_id"] == 42
    assert "exp" in claims
    assert "iat" in claims


def test_verify_token_roundtrip(service, account):
    token = service.create_token(account)
    assert service.verify_token(token)["sub"] == "maria"


def test_verify_token_rejects_modified_token(service, account):
    token = service.create_token(account)
    with pytest.raises(jwt.InvalidSignatureError):
        service.verify_token(token[:-1] + ("A" if token[-1] != "A" else "B"))


def test_admin_token_has_admin_role(session_factory, service):
    admin = UserAccount(
        username="admin",
        password_hash=bcrypt.hashpw(b"x", bcrypt.gensalt()).decode(),
        role=Role.ADMIN,
    )
    AuthRepository(session_factory).add(admin)
    claims = jwt.decode(
        service.create_token(admin), "test-secret-key", algorithms=["HS256"]
    )
    assert claims["role"] == "ADMIN"
    assert claims["researcher_id"] is None
