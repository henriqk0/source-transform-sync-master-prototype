from __future__ import annotations

from eo_lib.domain.base import Base
from eo_lib.domain.entities import Initiative, Organization  # noqa: F401

# Canonical entities are re-exported here for module-boundary convenience
# (Constitution Art. VII — no local redefinition). Portal-owned models below.
from research_domain.domain.entities import (  # noqa: F401
    Advisorship,
    Campus,
    Fellowship,
    KnowledgeArea,
    Researcher,
    ResearchGroup,
    ResearchProduction,
    University,
)
from research_domain.domain.entities.article import Article, ArticleType  # noqa: F401
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func


def _utcnow():
    return func.now()


class ResearcherCampus(Base):
    """Portal-owned boundary mapping: Researcher -> primary Campus
    (the source data carries the campus only as embedded JSON; canonical
    entities stay untouched — Art. VII)."""

    __tablename__ = "researcher_campuses"

    researcher_id = Column(Integer, ForeignKey("researchers.id"), primary_key=True)
    campus_id = Column(Integer, ForeignKey("organizational_units.id"), nullable=False)

    def __init__(self, researcher_id: int, campus_id: int) -> None:
        self.researcher_id = researcher_id
        self.campus_id = campus_id


class ResearcherSensitive(Base):
    """Portal-owned side table for LGPD-sensitive attributes extracted from
    the source files (identification id, birthday). Values are never exposed
    through any public endpoint; only their presence is reported (Art. V)."""

    __tablename__ = "researcher_sensitive"

    researcher_id = Column(Integer, ForeignKey("researchers.id"), primary_key=True)
    identification_id = Column(String(255), nullable=True)
    birthday = Column(String(10), nullable=True)

    def __init__(
        self,
        researcher_id: int,
        identification_id: str | None = None,
        birthday: str | None = None,
    ) -> None:
        self.researcher_id = researcher_id
        self.identification_id = identification_id
        self.birthday = birthday


class AuditLog(Base):
    """Portal-owned audit trail (Art. V): who did what to which subject.
    Details are masked before persistence; sensitive values never logged."""

    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    actor_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False)
    action = Column(String(100), nullable=False)
    target_id = Column(Integer, nullable=True)
    detail = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=_utcnow(), nullable=False)

    def __init__(
        self,
        actor_id: int,
        action: str,
        target_id: int | None = None,
        detail: str | None = None,
    ) -> None:
        self.actor_id = actor_id
        self.action = action
        self.target_id = target_id
        self.detail = detail


class ResearcherEmail(Base):
    """Portal-owned boundary table for professor emails (canonical Researcher
    has no email column; Art. VII keeps canonical entities untouched)."""

    __tablename__ = "researcher_emails"

    researcher_id = Column(Integer, ForeignKey("researchers.id"), primary_key=True)
    email = Column(String(255), primary_key=True)

    def __init__(self, researcher_id: int, email: str) -> None:
        self.researcher_id = researcher_id
        self.email = email


class ArticleCountByYear(Base):
    """Portal-owned pre-aggregation (ResearchData module) serving FR-003
    within the 2s p95 budget (Art. IV). Rebuilt during seeding."""

    __tablename__ = "article_counts_by_year"

    researcher_id = Column(Integer, ForeignKey("researchers.id"), primary_key=True)
    year = Column(Integer, primary_key=True)
    count = Column(Integer, nullable=False, default=0)

    def __init__(self, researcher_id: int, year: int, count: int) -> None:
        self.researcher_id = researcher_id
        self.year = year
        self.count = count
