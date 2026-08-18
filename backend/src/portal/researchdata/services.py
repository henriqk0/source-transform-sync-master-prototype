from __future__ import annotations

import bcrypt
from research_domain.domain.entities import Researcher, University

from portal.auth.models import Role, UserAccount
from portal.auth.repositories import AuthRepository
from portal.db import SessionFactory
from portal.observability import mask_sensitive
from portal.researchdata.repositories import RepositoryProvider


class RegistrationError(ValueError):
    """Raised when professor registration cannot complete (e.g. duplicate)."""


class EditForbidden(PermissionError):
    """Raised when an actor may not edit a given researcher (FR-018)."""


class ErasedError(RuntimeError):
    """Raised when acting on a professor whose personal data was erased."""


class ResearchDataService:
    """Portal service layer over canonical research_domain entities and
    portal-owned pre-aggregations (Art. I: Controller -> Service -> Repository)."""

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory
        self.provider = RepositoryProvider(session_factory)

    # -- public queries -----------------------------------------------------

    def search_professors(
        self, q: str | None, page: int, page_size: int
    ) -> tuple[list[dict], int]:
        researchers, total = self.provider.researchers.search(q, page, page_size)
        campus_map = self.provider.researcher_campuses.campus_map(
            [r.id for r in researchers]
        )
        campus_names = self._campus_names(campus_map.values())
        items = [
            {
                "id": r.id,
                "name": r.name,
                "affiliation": campus_names.get(campus_map.get(r.id)),
            }
            for r in researchers
        ]
        return items, total

    def get_profile(
        self,
        researcher_id: int,
        article_page: int = 1,
        article_page_size: int = 50,
    ) -> dict:
        researcher = self.provider.researchers.get_by_id(researcher_id)
        if researcher is None:
            raise KeyError(researcher_id)

        campus_id = self.provider.researcher_campuses.campus_id_for(researcher_id)
        affiliation = None
        locations: list[dict] = []
        if campus_id is not None:
            campus = self.provider.campuses.get_by_id(campus_id)
            if campus is not None:
                affiliation = campus.name
                locations.append(
                    {"id": campus.id, "name": campus.name, "type": "campus"}
                )
        university = self._find_university()
        if university is not None:
            locations.append(
                {
                    "id": university.id,
                    "name": university.name,
                    "type": "organization",
                }
            )

        projects = [
            {"id": i.id, "name": i.name, "status": i.status}
            for i in self.provider.initiatives.list_active_for_researcher(researcher_id)
        ]

        counts = [
            {"year": year, "count": count}
            for year, count in self.provider.article_counts.counts_for_researcher(
                researcher_id
            )
        ]

        articles, articles_total = self.provider.articles.list_for_researcher(
            researcher_id, article_page, article_page_size
        )
        article_items = [
            {
                "id": a.id,
                "title": a.title,
                "year": a.year,
                "type": a.type.value if a.type else None,
                "doi": a.doi,
            }
            for a in articles
        ]

        return {
            "id": researcher.id,
            "name": researcher.name,
            "affiliation": affiliation,
            "resume": researcher.resume,
            "current_projects": projects,
            "article_counts_by_year": counts,
            "locations": locations,
            "articles": article_items,
            "articles_total": articles_total,
            "article_page": article_page,
            "article_page_size": article_page_size,
        }

    # -- writes (US4) ---------------------------------------------------------

    def register_professor(
        self,
        name: str,
        username: str,
        password: str,
        emails: list[str] | None = None,
        resume: str | None = None,
    ) -> dict:
        """ADMIN-only registration: Researcher (DB only) + PROFESSOR account."""
        account_repository = AuthRepository(self._session_factory)
        if account_repository.get_by_username(username) is not None:
            raise RegistrationError("Username already exists")

        researcher = Researcher(name=name, resume=resume)
        self.provider.researchers.add(researcher)
        if emails:
            self.provider.researcher_emails.set_emails(researcher.id, emails)

        account_repository.add(
            UserAccount(
                username=username,
                password_hash=bcrypt.hashpw(
                    password.encode("utf-8"), bcrypt.gensalt()
                ).decode("utf-8"),
                role=Role.PROFESSOR,
                researcher_id=researcher.id,
            )
        )
        return {
            "id": account_repository.get_by_username(username).id,
            "username": username,
            "role": Role.PROFESSOR.value,
            "researcher_id": researcher.id,
        }

    def update_professor(
        self,
        researcher_id: int,
        actor: UserAccount,
        name: str | None = None,
        emails: list[str] | None = None,
        resume: str | None = None,
    ) -> dict:
        """Owner or ADMIN edit; changes apply to the DB only (never sources)."""
        researcher = self.provider.researchers.get_by_id(researcher_id)
        if researcher is None:
            raise KeyError(researcher_id)

        if AuthRepository(self._session_factory).is_erased(researcher_id):
            raise ErasedError(researcher_id)

        if actor.role != Role.ADMIN and actor.researcher_id != researcher_id:
            raise EditForbidden(researcher_id)

        if name is not None:
            researcher.name = name
        if resume is not None:
            researcher.resume = resume
        self.provider.researchers.update(researcher)
        if emails is not None:
            self.provider.researcher_emails.set_emails(researcher_id, emails)

        return {
            "id": researcher_id,
            "name": researcher.name,
            "emails": self.provider.researcher_emails.list_for_researcher(
                researcher_id
            ),
            "resume": researcher.resume,
        }

    # -- LGPD operations (FR-013, Art. V) -------------------------------------

    def personal_data(self, researcher_id: int, actor: UserAccount) -> dict:
        """LGPD access request: full values only for owner/ADMIN; sensitive
        fields reported by name only. Audited (masked)."""
        researcher = self.provider.researchers.get_by_id(researcher_id)
        if researcher is None:
            raise KeyError(researcher_id)
        if actor.role != Role.ADMIN and actor.researcher_id != researcher_id:
            raise EditForbidden(researcher_id)

        emails = self.provider.researcher_emails.list_for_researcher(researcher_id)
        sensitive = self.provider.researcher_sensitive.get(researcher_id)
        sensitive_fields = []
        if sensitive is not None:
            if sensitive.identification_id:
                sensitive_fields.append("identification_id")
            if sensitive.birthday:
                sensitive_fields.append("birthday")

        self.provider.audit_log.record(
            actor_id=actor.id,
            action="personal_data_access",
            target_id=researcher_id,
            detail=mask_sensitive(
                f"LGPD access for researcher {researcher_id} by {actor.username}"
            ),
        )
        return {
            "researcher_id": researcher_id,
            "name": researcher.name,
            "emails": emails,
            "resume": researcher.resume,
            "sensitive_fields": sensitive_fields,
        }

    def erase_personal_data(self, researcher_id: int, actor: UserAccount) -> dict:
        """LGPD erasure: remove personal data (emails, precise location,
        sensitive attributes) and anonymize the linked account. Research
        production data is kept. Audited (masked)."""
        researcher = self.provider.researchers.get_by_id(researcher_id)
        if researcher is None:
            raise KeyError(researcher_id)
        if actor.role != Role.ADMIN and actor.researcher_id != researcher_id:
            raise EditForbidden(researcher_id)

        erased_fields: list[str] = []
        if self.provider.researcher_emails.list_for_researcher(researcher_id):
            self.provider.researcher_emails.set_emails(researcher_id, [])
            erased_fields.append("emails")
        if self.provider.researcher_campuses.campus_id_for(researcher_id) is not None:
            self.provider.researcher_campuses.delete_for_researcher(researcher_id)
            erased_fields.append("location")
        if self.provider.researcher_sensitive.get(researcher_id) is not None:
            self.provider.researcher_sensitive.erase(researcher_id)
            erased_fields.append("identification_id")

        anonymized = False
        account_repository = AuthRepository(self._session_factory)
        for account in account_repository.get_all():
            if account.researcher_id == researcher_id:
                account.erased = True
                account_repository.update(account)
                anonymized = True

        self.provider.audit_log.record(
            actor_id=actor.id,
            action="personal_data_erasure",
            target_id=researcher_id,
            detail=mask_sensitive(
                f"LGPD erasure for researcher {researcher_id} by {actor.username}; "
                f"fields={erased_fields}"
            ),
        )
        return {
            "status": "erased",
            "erased_fields": erased_fields,
            "anonymized_account": anonymized,
        }

    # -- helpers ------------------------------------------------------------

    def _campus_names(self, campus_ids) -> dict[int, str]:
        names: dict[int, str] = {}
        for campus_id in campus_ids:
            if campus_id is None or campus_id in names:
                continue
            campus = self.provider.campuses.get_by_id(campus_id)
            if campus is not None:
                names[campus.id] = campus.name
        return names

    def _find_university(self) -> University | None:
        universities = self.provider.universities.get_all()
        return universities[0] if universities else None
