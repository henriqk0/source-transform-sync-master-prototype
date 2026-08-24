from __future__ import annotations

from typing import Generic, TypeVar

from eo_lib.domain.entities import Initiative, TeamMember
from eo_lib.domain.entities.initiative import initiative_persons
from libbase.infrastructure.interface import IRepository
from research_domain.domain.entities import (
    Advisorship,
    Campus,
    Fellowship,
    KnowledgeArea,
    ProductionType,
    Researcher,
    ResearchGroup,
    ResearchProduction,
    University,
)
from research_domain.domain.entities.article import Article, article_authors
from research_domain.domain.repositories import (
    AdvisorshipRepositoryInterface,
    ArticleRepositoryInterface,
    CampusRepositoryInterface,
    FellowshipRepositoryInterface,
    KnowledgeAreaRepositoryInterface,
    ResearcherRepositoryInterface,
    ResearchGroupRepositoryInterface,
    ResearchProductionRepositoryInterface,
    UniversityRepositoryInterface,
)
from sqlalchemy import delete, func
from sqlalchemy.orm import Session

from portal.db import SessionFactory
from portal.researchdata.models import (
    ArticleCountByYear,
    AuditLog,
    ResearcherCampus,
    ResearcherCnpq,
    ResearcherEmail,
    ResearcherSensitive,
)

T = TypeVar("T")


class SQLiteRepository(IRepository[T], Generic[T]):
    """SQLite-backed implementation of the libbase IRepository contract
    (the portal's counterpart to research_domain's memory/postgres
    strategies — plan Complexity Tracking)."""

    def __init__(
        self,
        session_factory: SessionFactory,
        entity_type: type,
        session: Session | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._entity_type = entity_type
        self._injected_session = session

    def _session(self) -> Session:
        if self._injected_session is not None:
            return self._injected_session
        return self._session_factory()

    def _commit_or_defer(self, session: Session) -> None:
        if self._injected_session is None:
            session.commit()

    def _release(self, session: Session) -> None:
        if self._injected_session is None:
            session.close()

    def add(self, entity: T) -> None:
        session = self._session()
        try:
            session.add(entity)
            self._commit_or_defer(session)
            session.flush()
            session.refresh(entity)
        finally:
            self._release(session)

    def get_by_id(self, entity_id) -> T | None:
        session = self._session()
        try:
            return session.get(self._entity_type, entity_id)
        finally:
            self._release(session)

    def get_all(self) -> list[T]:
        session = self._session()
        try:
            return session.query(self._entity_type).all()
        finally:
            self._release(session)

    def update(self, entity: T) -> None:
        session = self._session()
        try:
            session.merge(entity)
            self._commit_or_defer(session)
        finally:
            self._release(session)

    def delete(self, entity_id) -> None:
        session = self._session()
        try:
            entity = session.get(self._entity_type, entity_id)
            if entity:
                session.delete(entity)
                self._commit_or_defer(session)
        finally:
            self._release(session)


class SQLiteResearcherRepository(
    SQLiteRepository[Researcher], ResearcherRepositoryInterface
):
    def count(self) -> int:
        session = self._session()
        try:
            return session.query(Researcher).count()
        finally:
            self._release(session)

    def search(
        self, q: str | None, page: int, page_size: int
    ) -> tuple[list[Researcher], int]:
        session = self._session()
        try:
            query = session.query(Researcher)
            if q:
                query = query.filter(Researcher.name.ilike(f"%{q}%"))
            total = query.count()
            items = (
                query.order_by(Researcher.name)
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )
            return items, total
        finally:
            self._release(session)


class SQLiteArticleRepository(SQLiteRepository[Article], ArticleRepositoryInterface):
    def list_by_year(self, year: int) -> list[Article]:
        session = self._session()
        try:
            return session.query(Article).filter(Article.year == year).all()
        finally:
            self._release(session)

    def find_by_doi(self, doi: str) -> Article | None:
        session = self._session()
        try:
            return session.query(Article).filter(Article.doi == doi).first()
        finally:
            self._release(session)

    def find_by_title_year(self, title: str, year: int) -> Article | None:
        session = self._session()
        try:
            return (
                session.query(Article)
                .filter(Article.title == title, Article.year == year)
                .first()
            )
        finally:
            self._release(session)

    def list_for_researcher(
        self, researcher_id: int, page: int, page_size: int
    ) -> tuple[list[Article], int]:
        session = self._session()
        try:
            query = (
                session.query(Article)
                .join(article_authors, article_authors.c.article_id == Article.id)
                .filter(article_authors.c.researcher_id == researcher_id)
            )
            total = query.count()
            items = (
                query.order_by(Article.year.desc(), Article.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )
            return items, total
        finally:
            self._release(session)


class SQLiteUniversityRepository(
    SQLiteRepository[University], UniversityRepositoryInterface
):
    pass


class SQLiteCampusRepository(SQLiteRepository[Campus], CampusRepositoryInterface):
    pass


class SQLiteResearchGroupRepository(
    SQLiteRepository[ResearchGroup], ResearchGroupRepositoryInterface
):
    def add_member(self, member) -> None:
        session = self._session()
        try:
            session.add(member)
            self._commit_or_defer(session)
            session.refresh(member)
            return member
        finally:
            self._release(session)

    def remove_member(self, member_id: int) -> bool:
        session = self._session()
        try:
            member = session.get(TeamMember, member_id)
            if member:
                session.delete(member)
                self._commit_or_defer(session)
                return True
            return False
        finally:
            self._release(session)

    def get_members(self, team_id: int) -> list[TeamMember]:
        session = self._session()
        try:
            return session.query(TeamMember).filter(TeamMember.team_id == team_id).all()
        finally:
            self._release(session)


class SQLiteKnowledgeAreaRepository(
    SQLiteRepository[KnowledgeArea], KnowledgeAreaRepositoryInterface
):
    def find_by_name(self, name: str) -> KnowledgeArea | None:
        session = self._session()
        try:
            return (
                session.query(KnowledgeArea)
                .filter(func.lower(KnowledgeArea.name) == name.lower())
                .first()
            )
        finally:
            self._release(session)


class SQLiteAdvisorshipRepository(
    SQLiteRepository[Advisorship], AdvisorshipRepositoryInterface
):
    pass


class SQLiteFellowshipRepository(
    SQLiteRepository[Fellowship], FellowshipRepositoryInterface
):
    pass


class SQLiteResearchProductionRepository(
    SQLiteRepository[ResearchProduction], ResearchProductionRepositoryInterface
):
    pass


class SQLiteInitiativeRepository(SQLiteRepository[Initiative]):
    def add_person(self, initiative_id: int, person_id: int) -> None:
        session = self._session()
        try:
            session.execute(
                initiative_persons.insert().values(
                    initiative_id=initiative_id, person_id=person_id
                )
            )
            self._commit_or_defer(session)
        finally:
            self._release(session)

    def list_active_for_researcher(self, researcher_id: int) -> list[Initiative]:
        session = self._session()
        try:
            return (
                session.query(Initiative)
                .join(
                    initiative_persons,
                    initiative_persons.c.initiative_id == Initiative.id,
                )
                .filter(
                    initiative_persons.c.person_id == researcher_id,
                    func.lower(Initiative.status) == "active",
                )
                .order_by(Initiative.name)
                .all()
            )
        finally:
            self._release(session)


class SQLiteProductionTypeRepository(SQLiteRepository[ProductionType]):
    pass


class ResearcherCampusRepository:
    """Portal-owned mapping repository (Researcher -> primary Campus)."""

    def __init__(
        self, session_factory: SessionFactory, session: Session | None = None
    ) -> None:
        self._session_factory = session_factory
        self._injected_session = session

    def _session(self) -> Session:
        if self._injected_session is not None:
            return self._injected_session
        return self._session_factory()

    def _commit_or_defer(self, session: Session) -> None:
        if self._injected_session is None:
            session.commit()

    def _release(self, session: Session) -> None:
        if self._injected_session is None:
            session.close()

    def upsert(self, researcher_id: int, campus_id: int) -> None:
        session = self._session()
        try:
            row = session.get(ResearcherCampus, researcher_id)
            if row:
                row.campus_id = campus_id
            else:
                session.add(ResearcherCampus(researcher_id, campus_id))
            self._commit_or_defer(session)
        finally:
            self._release(session)

    def delete_for_researcher(self, researcher_id: int) -> None:
        session = self._session()
        try:
            session.execute(
                delete(ResearcherCampus).where(
                    ResearcherCampus.researcher_id == researcher_id
                )
            )
            self._commit_or_defer(session)
        finally:
            self._release(session)

    def campus_id_for(self, researcher_id: int) -> int | None:
        session = self._session()
        try:
            row = session.get(ResearcherCampus, researcher_id)
            return row.campus_id if row else None
        finally:
            self._release(session)

    def campus_map(self, researcher_ids: list[int]) -> dict[int, int]:
        session = self._session()
        try:
            rows = (
                session.query(ResearcherCampus)
                .filter(ResearcherCampus.researcher_id.in_(researcher_ids))
                .all()
            )
            return {r.researcher_id: r.campus_id for r in rows}
        finally:
            self._release(session)


class ResearcherSensitiveRepository:
    """Portal-owned repository for LGPD-sensitive attributes (Art. V)."""

    def __init__(
        self, session_factory: SessionFactory, session: Session | None = None
    ) -> None:
        self._session_factory = session_factory
        self._injected_session = session

    def _session(self) -> Session:
        if self._injected_session is not None:
            return self._injected_session
        return self._session_factory()

    def _commit_or_defer(self, session: Session) -> None:
        if self._injected_session is None:
            session.commit()

    def _release(self, session: Session) -> None:
        if self._injected_session is None:
            session.close()

    def upsert(
        self,
        researcher_id: int,
        identification_id: str | None = None,
        birthday: str | None = None,
    ) -> None:
        session = self._session()
        try:
            row = session.get(ResearcherSensitive, researcher_id)
            if row is None:
                row = ResearcherSensitive(researcher_id)
                session.add(row)
            row.identification_id = identification_id
            row.birthday = birthday
            self._commit_or_defer(session)
        finally:
            self._release(session)

    def get(self, researcher_id: int) -> ResearcherSensitive | None:
        session = self._session()
        try:
            return session.get(ResearcherSensitive, researcher_id)
        finally:
            self._release(session)

    def erase(self, researcher_id: int) -> None:
        session = self._session()
        try:
            row = session.get(ResearcherSensitive, researcher_id)
            if row is not None:
                session.delete(row)
            self._commit_or_defer(session)
        finally:
            self._release(session)


class AuditLogRepository:
    """Portal-owned audit trail repository (Art. V)."""

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def record(
        self,
        actor_id: int,
        action: str,
        target_id: int | None = None,
        detail: str | None = None,
    ) -> None:
        session = self._session_factory()
        try:
            session.add(AuditLog(actor_id, action, target_id, detail))
            session.commit()
        finally:
            session.close()


class ResearcherEmailRepository:
    """Portal-owned repository for professor emails (owner/ADMIN editable)."""

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory
        self._injected_session = None

    def _session(self) -> Session:
        return self._session_factory()

    def _commit_or_defer(self, session: Session) -> None:
        session.commit()

    def _release(self, session: Session) -> None:
        session.close()

    def list_for_researcher(self, researcher_id: int) -> list[str]:
        session = self._session()
        try:
            rows = (
                session.query(ResearcherEmail)
                .filter(ResearcherEmail.researcher_id == researcher_id)
                .order_by(ResearcherEmail.email)
                .all()
            )
            return [row.email for row in rows]
        finally:
            self._release(session)

    def set_emails(self, researcher_id: int, emails: list[str]) -> None:
        session = self._session()
        try:
            session.query(ResearcherEmail).filter(
                ResearcherEmail.researcher_id == researcher_id
            ).delete()
            for email in emails:
                session.add(ResearcherEmail(researcher_id, email))
            self._commit_or_defer(session)
        finally:
            self._release(session)


class ResearcherCnpqRepository:
    """Portal-owned repository linking professors to their CNPq ids."""

    def __init__(
        self, session_factory: SessionFactory, session: Session | None = None
    ) -> None:
        self._session_factory = session_factory
        self._injected_session = session

    def _session(self) -> Session:
        if self._injected_session is not None:
            return self._injected_session
        return self._session_factory()

    def _commit_or_defer(self, session: Session) -> None:
        if self._injected_session is None:
            session.commit()

    def _release(self, session: Session) -> None:
        if self._injected_session is None:
            session.close()

    def researcher_for(self, cnpq_id: str) -> int | None:
        session = self._session()
        try:
            row = (
                session.query(ResearcherCnpq)
                .filter(ResearcherCnpq.cnpq_id == cnpq_id)
                .first()
            )
            return row.researcher_id if row is not None else None
        finally:
            self._release(session)

    def record(self, researcher_id: int, cnpq_id: str) -> None:
        session = self._session()
        try:
            exists = (
                session.query(ResearcherCnpq)
                .filter(ResearcherCnpq.cnpq_id == cnpq_id)
                .first()
            )
            if exists is None:
                session.add(ResearcherCnpq(researcher_id, cnpq_id))
                self._commit_or_defer(session)
        finally:
            self._release(session)


class ArticleCountRepository:
    """Portal-owned pre-aggregation repository (FR-003, Art. IV)."""

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory
        self._injected_session = None

    def _session(self) -> Session:
        return self._session_factory()

    def _commit_or_defer(self, session: Session) -> None:
        session.commit()

    def _release(self, session: Session) -> None:
        session.close()

    def upsert_counts(self, rows: list[tuple[int, int, int]]) -> None:
        """rows: (researcher_id, year, count)"""
        session = self._session_factory()
        try:
            for researcher_id, year, count in rows:
                row = (
                    session.query(ArticleCountByYear)
                    .filter(
                        ArticleCountByYear.researcher_id == researcher_id,
                        ArticleCountByYear.year == year,
                    )
                    .first()
                )
                if row:
                    row.count = count
                else:
                    session.add(ArticleCountByYear(researcher_id, year, count))
            self._commit_or_defer(session)
        finally:
            self._release(session)

    def counts_for_researcher(self, researcher_id: int) -> list[tuple[int, int]]:
        session = self._session_factory()
        try:
            rows = (
                session.query(ArticleCountByYear)
                .filter(ArticleCountByYear.researcher_id == researcher_id)
                .order_by(ArticleCountByYear.year.desc())
                .all()
            )
            return [(r.year, r.count) for r in rows]
        finally:
            self._release(session)

    def delete_for_researcher(self, researcher_id: int) -> None:
        session = self._session_factory()
        try:
            session.execute(
                delete(ArticleCountByYear).where(
                    ArticleCountByYear.researcher_id == researcher_id
                )
            )
            self._commit_or_defer(session)
        finally:
            self._release(session)

    def rebuild(self) -> None:
        """Recompute the whole pre-aggregation from article author links."""
        session = self._session_factory()
        try:
            session.query(ArticleCountByYear).delete()
            pairs = (
                session.query(
                    article_authors.c.researcher_id,
                    Article.year,
                    func.count(Article.id),
                )
                .join(Article, Article.id == article_authors.c.article_id)
                .group_by(article_authors.c.researcher_id, Article.year)
                .all()
            )
            for researcher_id, year, count in pairs:
                session.add(ArticleCountByYear(researcher_id, year, count))
            self._commit_or_defer(session)
        finally:
            self._release(session)


class RepositoryProvider:
    """Single entry point for all repository instances (module boundary)."""

    def __init__(
        self, session_factory: SessionFactory, session: Session | None = None
    ) -> None:
        self.researchers = SQLiteResearcherRepository(
            session_factory, Researcher, session
        )
        self.articles = SQLiteArticleRepository(session_factory, Article, session)
        self.initiatives = SQLiteInitiativeRepository(
            session_factory, Initiative, session
        )
        self.universities = SQLiteUniversityRepository(
            session_factory, University, session
        )
        self.campuses = SQLiteCampusRepository(session_factory, Campus, session)
        self.groups = SQLiteResearchGroupRepository(
            session_factory, ResearchGroup, session
        )
        self.areas = SQLiteKnowledgeAreaRepository(
            session_factory, KnowledgeArea, session
        )
        self.advisorships = SQLiteAdvisorshipRepository(
            session_factory, Advisorship, session
        )
        self.fellowships = SQLiteFellowshipRepository(
            session_factory, Fellowship, session
        )
        self.productions = SQLiteResearchProductionRepository(
            session_factory, ResearchProduction, session
        )
        self.production_types = SQLiteProductionTypeRepository(
            session_factory, ProductionType, session
        )
        self.article_counts = ArticleCountRepository(session_factory)
        self.researcher_campuses = ResearcherCampusRepository(session_factory, session)
        self.researcher_emails = ResearcherEmailRepository(session_factory)
        self.researcher_cnpqs = ResearcherCnpqRepository(session_factory, session)
        self.researcher_sensitive = ResearcherSensitiveRepository(
            session_factory, session
        )
        self.audit_log = AuditLogRepository(session_factory)
