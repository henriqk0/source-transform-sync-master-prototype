"""Ingestion service: parquet/JSON → canonical entity mapping and atomic seed.

Source files in `backend/data/` are read-only inputs (FR-021): this module
never writes to them. Mapping table follows data-model.md section 6.
"""

from __future__ import annotations

import json
import os
import re
from datetime import date
from typing import Any

import pyarrow.parquet as pq
from eo_lib.domain.entities import Initiative
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
from research_domain.domain.entities.article import Article, ArticleType

from portal.db import SessionFactory
from portal.ingestion.models import SyncStateStatus
from portal.ingestion.repositories import SyncStateRepository
from portal.observability import mask_sensitive
from portal.researchdata.repositories import RepositoryProvider

ARTICLE_TYPE_ALIASES = {
    "journal": ArticleType.JOURNAL,
    "conference event": ArticleType.CONFERENCE_EVENT,
    "conference_event": ArticleType.CONFERENCE_EVENT,
    "conference": ArticleType.CONFERENCE_EVENT,
}
ACTIVE_INITIATIVE_STATUSES = {"active", "in progress"}

# Lattes id embedded in the canonical cnpq_url; used to link admin-created
# logins to professors already saved by the seed (data-model.md §2/§6).
_LATTES_URL_PATTERN = re.compile(r"lattes\.cnpq\.br/(\d+)")

COUNTS_KEYS = [
    "researchers",
    "articles",
    "initiatives",
    "research_groups",
    "campuses",
    "organizations",
    "knowledge_areas",
    "research_productions",
    "advisorships",
    "fellowships",
]


def _as_list(value: Any) -> list:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return []
    return value


def _as_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _lattes_id_from_cnpq_url(url: Any) -> str | None:
    if not url:
        return None
    match = _LATTES_URL_PATTERN.search(str(url))
    return match.group(1) if match else None


class SeedError(RuntimeError):
    """Base class for seed refusal reasons."""


class SeedAlreadyRunning(SeedError):
    pass


class DatabaseNotEmpty(SeedError):
    pass


class IngestionService:
    def __init__(self, session_factory: SessionFactory, data_dir: str) -> None:
        self._session_factory = session_factory
        self._data_dir = data_dir
        self._provider = RepositoryProvider(session_factory)
        self._sync_states = SyncStateRepository(session_factory)
        self._errors: list[dict[str, str | None]] = []
        self._counts: dict[str, int] = {key: 0 for key in COUNTS_KEYS}

    def sync_status(self) -> dict:
        return self._sync_states.get_state_dict()

    def _ensure_empty(self) -> None:
        self._ensure_not_running()
        self._ensure_empty_db()

    def _ensure_not_running(self) -> None:
        state = self._sync_states.get()
        if state is not None and state.status == SyncStateStatus.RUNNING:
            raise SeedAlreadyRunning("Seed already running")

    def _ensure_empty_db(self) -> None:
        if self._provider.researchers.count() > 0:
            raise DatabaseNotEmpty("Database already seeded")

    def seed(self, check_running: bool = True, begin_state: bool = True) -> None:
        """Populate the database from vendored source files (atomic)."""
        if check_running:
            self._ensure_not_running()
        self._ensure_empty_db()
        if begin_state:
            self._sync_states.begin()
        session = self._session_factory()
        self._provider = RepositoryProvider(self._session_factory, session)
        try:
            self._load_all(session)
            self._provider.article_counts.rebuild()
            session.commit()
            self._sync_states.succeed(self._counts, self._errors)
        except Exception as exc:
            session.rollback()
            error = {
                "file": self._current_file or "seed",
                "record": None,
                "detail": mask_sensitive(str(exc))[:500],
            }
            self._sync_states.fail([error])
            raise
        finally:
            session.close()
            self._provider = RepositoryProvider(self._session_factory)

    _current_file: str | None = None

    # ------------------------------------------------------------------
    # Loaders: each source file maps into canonical entities (section 6).
    # ------------------------------------------------------------------

    def _read_rows(self, filename: str) -> list[dict]:
        path = os.path.join(self._data_dir, filename)
        if not os.path.exists(path):
            return []
        return pq.read_table(path).to_pylist()

    def _record_error(self, filename: str, record: str | None, detail: str) -> None:
        self._errors.append(
            {
                "file": filename,
                "record": record,
                "detail": mask_sensitive(detail)[:500],
            }
        )

    def _load_organizations(self) -> None:
        self._current_file = "organizations_canonical.parquet"
        existing = {u.id for u in self._provider.universities.get_all()}
        for row in self._read_rows(self._current_file):
            if row.get("id") in existing:
                continue
            self._provider.universities.add(
                University(
                    id=row.get("id"),
                    name=row["name"],
                    short_name=row.get("short_name"),
                )
            )
            self._counts["organizations"] += 1
            existing.add(row.get("id"))

    def _load_campuses(self) -> None:
        self._current_file = "campuses_canonical.parquet"
        existing = {c.id for c in self._provider.campuses.get_all()}
        for row in self._read_rows(self._current_file):
            if row.get("id") in existing:
                continue
            self._provider.campuses.add(
                Campus(
                    id=row.get("id"),
                    name=row["name"],
                    organization_id=row.get("organization_id"),
                )
            )
            self._counts["campuses"] += 1
            existing.add(row.get("id"))

    def _ensure_campus(self, name: str | None) -> None:
        if not name:
            return
        existing = {c.name for c in self._provider.campuses.get_all()}
        if name in existing:
            return
        universities = self._provider.universities.get_all()
        university = universities[0] if universities else None
        self._provider.campuses.add(
            Campus(name=name, organization_id=university.id if university else None)
        )
        self._counts["campuses"] += 1

    def _load_knowledge_areas(self) -> None:
        self._current_file = "knowledge_areas_canonical.parquet"
        existing = {a.name for a in self._provider.areas.get_all()}
        for row in self._read_rows(self._current_file):
            if row["name"] in existing:
                continue
            self._provider.areas.add(KnowledgeArea(name=row["name"]))
            self._counts["knowledge_areas"] += 1
            existing.add(row["name"])

    def _load_production_types(self) -> None:
        self._current_file = "production_types_canonical.parquet"
        existing = {t.name for t in self._provider.production_types.get_all()}
        for row in self._read_rows(self._current_file):
            if row["name"] in existing:
                continue
            self._provider.production_types.add(ProductionType(name=row["name"]))
            existing.add(row["name"])

    def _load_research_groups(self) -> None:
        self._current_file = "research_groups_canonical.parquet"
        for row in self._read_rows(self._current_file):
            self._provider.groups.add(
                ResearchGroup(
                    id=row.get("id"),
                    name=row["name"],
                    short_name=row.get("short_name"),
                    campus_id=row.get("campus_id"),
                    cnpq_url=row.get("cnpq_url"),
                    site=row.get("site"),
                )
            )
            self._counts["research_groups"] += 1

    def _load_articles(self) -> None:
        self._current_file = "articles_canonical.parquet"
        for row in self._read_rows(self._current_file):
            article_type = ARTICLE_TYPE_ALIASES.get(
                str(row.get("type") or "").lower(), ArticleType.JOURNAL
            )
            self._provider.articles.add(
                Article(
                    id=row.get("id"),
                    title=row["title"],
                    doi=row.get("doi"),
                    year=row.get("year"),
                    type=article_type,
                    journal_conference=row.get("journal_conference"),
                    volume=row.get("volume"),
                    pages=row.get("pages"),
                )
            )
            self._counts["articles"] += 1

    def _link_article_authors(self) -> None:
        self._current_file = "production_authors_canonical.parquet"
        for row in self._read_rows(self._current_file):
            article = self._provider.articles.get_by_id(row["production_id"])
            researcher = self._provider.researchers.get_by_id(row["researcher_id"])
            if article is None or researcher is None:
                self._record_error(
                    self._current_file,
                    str(row.get("production_id")),
                    "article or researcher not found for author link",
                )
                continue
            article.authors = [*article.authors, researcher]
            self._provider.articles.update(article)

    def _load_researchers(self) -> None:
        self._current_file = "researchers_only_canonical.parquet"
        for row in self._read_rows(self._current_file):
            campus_info = _as_list(row.get("campus"))
            campus_name = None
            if isinstance(campus_info, list):
                campus_name = campus_info[0].get("name") if campus_info else None
            elif isinstance(campus_info, dict):
                campus_name = campus_info.get("name")
            self._ensure_campus(campus_name)

            researcher = Researcher(
                id=row.get("id"),
                name=row["name"],
                cnpq_url=row.get("cnpq_url"),
                google_scholar_url=row.get("google_scholar_url"),
                resume=row.get("resume"),
            )
            self._provider.researchers.add(researcher)
            self._counts["researchers"] += 1

            lattes_id = _lattes_id_from_cnpq_url(row.get("cnpq_url"))
            if lattes_id:
                self._provider.researcher_cnpqs.record(researcher.id, lattes_id)

            if row.get("identification_id") or row.get("birthday"):
                birthday = row.get("birthday")
                self._provider.researcher_sensitive.upsert(
                    researcher.id,
                    identification_id=row.get("identification_id"),
                    birthday=str(birthday)[:10] if birthday else None,
                )

            if campus_name:
                campus = next(
                    (
                        c
                        for c in self._provider.campuses.get_all()
                        if c.name == campus_name
                    ),
                    None,
                )
                if campus is not None:
                    self._provider.researcher_campuses.upsert(researcher.id, campus.id)

            for article in _as_list(row.get("articles")):
                if not isinstance(article, dict) or "id" not in article:
                    continue
                existing = self._provider.articles.get_by_id(article["id"])
                if existing is None:
                    self._record_error(
                        self._current_file,
                        str(row["id"]),
                        f"embedded article {article.get('id')} not found",
                    )
                    continue
                if researcher not in existing.authors:
                    existing.authors = [*existing.authors, researcher]
                    self._provider.articles.update(existing)

    def _load_initiatives(self) -> None:
        self._current_file = "initiatives_canonical.parquet"
        for row in self._read_rows(self._current_file):
            initiative = Initiative(
                id=row.get("id"),
                name=row["name"],
                status=row.get("status"),
                start_date=_as_date(row.get("start_date")),
                end_date=_as_date(row.get("end_date")),
            )
            self._provider.initiatives.add(initiative)
            self._counts["initiatives"] += 1

            for member in _as_list(row.get("team")):
                person_id = (
                    member.get("person_id") if isinstance(member, dict) else None
                )
                if person_id is None:
                    continue
                researcher = self._provider.researchers.get_by_id(person_id)
                if researcher is None:
                    self._record_error(
                        self._current_file,
                        str(row["id"]),
                        f"team references unknown person {person_id}",
                    )
                    continue
                self._provider.initiatives.add_person(initiative.id, researcher.id)

    def _load_research_productions(self) -> None:
        self._current_file = "research_productions_canonical.parquet"
        for row in self._read_rows(self._current_file):
            self._provider.productions.add(
                ResearchProduction(
                    title=row["title"],
                    year=row.get("year"),
                    production_type_id=row.get("production_type_id"),
                    publisher=row.get("publisher"),
                    isbn=row.get("isbn"),
                    edition=row.get("edition"),
                    book_title=row.get("book_title"),
                    pages=row.get("pages"),
                    version=row.get("version"),
                    platform=row.get("platform"),
                    link=row.get("link"),
                )
            )
            self._counts["research_productions"] += 1

    def _load_advisorships(self) -> None:
        self._current_file = "advisorships_canonical.parquet"
        initiative_ids = {i.id for i in self._provider.initiatives.get_all()} | {
            i.id for i in self._provider.advisorships.get_all()
        }
        for row in self._read_rows(self._current_file):
            if row.get("id") in initiative_ids:
                # Same id as an initiative (colliding source records);
                # the initiative row wins, difference is recorded.
                self._record_error(
                    self._current_file,
                    str(row.get("id")),
                    "id already exists as an initiative; advisorship row skipped",
                )
                continue
            self._provider.advisorships.add(
                Advisorship(
                    id=row.get("id"),
                    name=row["name"],
                    status=row.get("status"),
                    description=row.get("description"),
                    start_date=_as_date(row.get("start_date")),
                    end_date=_as_date(row.get("end_date")),
                )
            )
            self._counts["advisorships"] += 1

    def _load_fellowships(self) -> None:
        self._current_file = "fellowships_canonical.parquet"
        for row in self._read_rows(self._current_file):
            self._provider.fellowships.add(
                Fellowship(
                    name=row["name"],
                    description=row.get("description"),
                    value=row.get("value"),
                )
            )
            self._counts["fellowships"] += 1

    def _load_all(self, session) -> None:
        self._load_organizations()
        self._load_campuses()
        self._load_knowledge_areas()
        self._load_production_types()
        self._load_research_groups()
        self._load_articles()
        self._load_researchers()
        self._load_initiatives()
        self._load_advisorships()
        self._load_research_productions()
        self._load_fellowships()
        self._link_article_authors()
