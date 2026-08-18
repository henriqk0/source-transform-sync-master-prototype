"""E2E test backend: seeds a temporary SQLite database with sample data and
serves the portal API for Playwright journeys.

Usage: PORTAL_DB_PATH=/tmp/e2e.db python tests/scripts/e2e_server.py
"""

from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import bcrypt  # noqa: E402
import uvicorn  # noqa: E402
from eo_lib.domain.entities import Initiative  # noqa: E402
from research_domain.domain.entities import Campus, Researcher, University  # noqa: E402
from research_domain.domain.entities.article import Article, ArticleType  # noqa: E402

from portal.auth.models import Role, UserAccount  # noqa: E402
from portal.auth.repositories import AuthRepository  # noqa: E402
from portal.config import load_settings  # noqa: E402
from portal.db import create_session_factory, init_db  # noqa: E402
from portal.ingestion.repositories import SyncStateRepository  # noqa: E402
from portal.main import create_app  # noqa: E402
from portal.researchdata.repositories import RepositoryProvider  # noqa: E402

SAMPLES = [
    ("Maria Alice Veiga Ferreira De Souza", "Vila Velha", [2023, 2024, 2024, 2025]),
    ("Carlos Roberto Pires Campos", "Serra", [2022, 2023]),
    ("Luciano Lessa Lorenzoni", "Serra", []),
    ("Ana Paula Sem Dados", "Serra", []),
]


def seed(session_factory) -> dict[int, str]:
    provider = RepositoryProvider(session_factory)
    university = University(
        name="Instituto Federal do Espirito Santo", short_name="IFES"
    )
    provider.universities.add(university)
    campuses: dict[str, int] = {}
    researchers: dict[int, str] = {}

    for name, campus_name, article_years in SAMPLES:
        campus_id = campuses.get(campus_name)
        if campus_id is None:
            campus = Campus(name=campus_name, organization_id=university.id)
            provider.campuses.add(campus)
            campuses[campus_name] = campus.id
            campus_id = campus.id

        researcher = Researcher(name=name)
        provider.researchers.add(researcher)
        provider.researcher_campuses.upsert(researcher.id, campus_id)
        researchers[researcher.id] = name

        if name != "Ana Paula Sem Dados":
            project = Initiative(
                name=f"Projeto Ativo de {name.split()[0]}", status="Active"
            )
            provider.initiatives.add(project)
            provider.initiatives.add_person(project.id, researcher.id)

        for year in article_years:
            article = Article(
                title=f"Publicação {year} de {name.split()[0]}",
                year=year,
                type=ArticleType.JOURNAL,
            )
            provider.articles.add(article)
            article.authors = [researcher]
            provider.articles.update(article)
    provider.article_counts.rebuild()

    auth = AuthRepository(session_factory)
    auth.add(
        UserAccount(
            username="admin",
            password_hash=bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode(),
            role=Role.ADMIN,
        )
    )
    professor_researcher_id = next(iter(researchers))
    auth.add(
        UserAccount(
            username="maria",
            password_hash=bcrypt.hashpw(b"maria123", bcrypt.gensalt()).decode(),
            role=Role.PROFESSOR,
            researcher_id=professor_researcher_id,
        )
    )

    sync = SyncStateRepository(session_factory)
    sync.get()  # ensure the single state row exists
    sync.succeed(
        {
            "researchers": len(researchers),
            "articles": sum(len(article_years) for _, _, article_years in SAMPLES),
        }
    )
    return researchers


def main() -> None:
    if "PORTAL_DB_PATH" not in os.environ:
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.environ["PORTAL_DB_PATH"] = path
        print(f"Using temp DB: {path}")
    settings = load_settings()
    session_factory = create_session_factory(settings.db_path)
    init_db(session_factory)
    seed(session_factory)
    app = create_app(session_factory=session_factory, settings=settings)
    # Port 8001: the dev server owns 8000, and Playwright must never reuse it.
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="warning")


if __name__ == "__main__":
    main()
