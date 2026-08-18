import bcrypt
import pytest
from sqlalchemy.exc import IntegrityError

from portal.auth.models import Role, UserAccount
from portal.auth.repositories import AuthRepository


@pytest.fixture
def repo(session_factory):
    return AuthRepository(session_factory)


class TestUserAccountModel:
    def test_username_unique(self, session_factory):
        repo = AuthRepository(session_factory)
        repo.add(UserAccount(username="maria", password_hash="h", role=Role.ADMIN))
        with pytest.raises(IntegrityError):
            repo.add(UserAccount(username="maria", password_hash="h2", role=Role.ADMIN))

    def test_password_stored_hashed_with_bcrypt(self, session_factory):
        password = "supersecret123"
        account = UserAccount(
            username="joao",
            password_hash=bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
            role=Role.PROFESSOR,
        )
        assert account.password_hash != password
        assert bcrypt.checkpw(password.encode(), account.password_hash.encode())

    def test_invalid_role_rejected(self):
        with pytest.raises(ValueError):
            UserAccount(username="x", password_hash="h", role="SUPERUSER")  # type: ignore[arg-type]

    def test_professor_account_requires_researcher(self, session_factory):
        repo = AuthRepository(session_factory)
        with pytest.raises(ValueError):
            repo.add(
                UserAccount(username="sem", password_hash="h", role=Role.PROFESSOR)
            )


class TestAuthRepository:
    def test_add_and_get_by_username(self, repo, session_factory):
        from research_domain.domain.entities import Researcher

        from portal.researchdata.repositories import RepositoryProvider

        provider = RepositoryProvider(session_factory)
        researcher = Researcher(name="Maria Souza")
        provider.researchers.add(researcher)

        repo.add(
            UserAccount(
                username="maria",
                password_hash="h",
                role=Role.PROFESSOR,
                researcher_id=researcher.id,
            )
        )
        loaded = repo.get_by_username("maria")
        assert loaded is not None
        assert loaded.role == Role.PROFESSOR
        assert loaded.researcher_id == researcher.id
        assert repo.get_by_username("ghost") is None

    def test_update_and_delete(self, repo, session_factory):
        from research_domain.domain.entities import Researcher

        from portal.researchdata.repositories import RepositoryProvider

        provider = RepositoryProvider(session_factory)
        researcher = Researcher(name="Admin A")
        provider.researchers.add(researcher)
        account = UserAccount(
            username="admin",
            password_hash="h",
            role=Role.ADMIN,
        )
        repo.add(account)
        account.password_hash = "h2"
        repo.update(account)
        assert repo.get_by_username("admin").password_hash == "h2"
        repo.delete(account.id)
        assert repo.get_by_username("admin") is None

    def test_admin_account_may_have_null_researcher(self, repo):
        repo.add(UserAccount(username="root", password_hash="h", role=Role.ADMIN))
        assert repo.get_by_username("root").researcher_id is None
