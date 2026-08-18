"""T049 — LGPD service operations: access export, erasure, audit trail."""

from __future__ import annotations

import bcrypt
import pytest
from research_domain.domain.entities import Campus, Researcher, University
from sqlalchemy import text

from portal.auth.models import Role, UserAccount
from portal.auth.repositories import AuthRepository
from portal.researchdata.repositories import RepositoryProvider
from portal.researchdata.services import (
    EditForbidden,
    ErasedError,
    ResearchDataService,
)


@pytest.fixture
def service(session_factory) -> ResearchDataService:
    provider = RepositoryProvider(session_factory)
    provider.researchers.add(Researcher(id=1, name="Maria"))
    provider.universities.add(University(id=1, name="IFES"))
    provider.campuses.add(Campus(id=1, name="Vila Velha", organization_id=1))
    provider.researcher_campuses.upsert(1, 1)
    provider.researcher_emails.set_emails(1, ["maria@ifes.edu.br"])
    AuthRepository(session_factory).add(
        UserAccount(
            username="maria",
            password_hash=bcrypt.hashpw(b"secret123", bcrypt.gensalt()).decode(),
            role=Role.PROFESSOR,
            researcher_id=1,
        )
    )
    return ResearchDataService(session_factory)


def _owner(session_factory) -> UserAccount:
    return AuthRepository(session_factory).get_by_username("maria")


def test_access_export_shape(session_factory, service):
    data = service.personal_data(1, _owner(session_factory))
    assert data["researcher_id"] == 1
    assert data["name"] == "Maria"
    assert data["emails"] == ["maria@ifes.edu.br"]
    assert isinstance(data["sensitive_fields"], list)


def test_access_forbidden_for_non_owner(session_factory, service):
    other = UserAccount(
        username="outro",
        password_hash=bcrypt.hashpw(b"x", bcrypt.gensalt()).decode(),
        role=Role.PROFESSOR,
        researcher_id=2,
    )
    with pytest.raises(EditForbidden):
        service.personal_data(1, other)


def test_erasure_anonymizes_and_keeps_research_data(session_factory, service):
    result = service.erase_personal_data(1, _owner(session_factory))
    assert result["status"] == "erased"
    assert result["anonymized_account"] is True
    assert "emails" in result["erased_fields"]

    provider = RepositoryProvider(session_factory)
    assert provider.researchers.get_by_id(1) is not None  # research data kept
    assert provider.researcher_emails.list_for_researcher(1) == []
    assert provider.researcher_campuses.campus_id_for(1) is None


def test_erased_account_flag_set(session_factory, service):
    service.erase_personal_data(1, _owner(session_factory))
    account = AuthRepository(session_factory).get_by_username("maria")
    assert account.erased is True


def test_editing_erased_professor_raises(session_factory, service):
    service.erase_personal_data(1, _owner(session_factory))
    with pytest.raises(ErasedError):
        service.update_professor(1, _owner(session_factory), emails=["x@ifes.edu.br"])


def test_audit_trail_entries_masked(session_factory, service):
    service.personal_data(1, _owner(session_factory))
    service.erase_personal_data(1, _owner(session_factory))

    session = session_factory()
    try:
        rows = session.execute(
            text("SELECT action, detail FROM audit_log ORDER BY id")
        ).fetchall()
    finally:
        session.close()
    assert [action for action, _ in rows] == [
        "personal_data_access",
        "personal_data_erasure",
    ]
    for _, detail in rows:
        assert "maria@ifes.edu.br" not in (detail or "")
        assert "LGPD-" not in (detail or "")
