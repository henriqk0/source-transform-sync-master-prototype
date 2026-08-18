"""N+1 regression guard for profile assembly (Constitution Art. IV)."""

from research_domain.domain.entities import Campus, Researcher, University
from research_domain.domain.entities.article import Article, ArticleType
from sqlalchemy import event

from portal.researchdata.services import ResearchDataService


def test_profile_assembly_query_count_is_bounded(session_factory):
    service = ResearchDataService(session_factory)

    university = University(name="IFES", short_name="IFES")
    service.provider.universities.add(university)
    campus = Campus(name="Serra", organization_id=university.id)
    service.provider.campuses.add(campus)

    researchers = []
    for i in range(30):
        researcher = Researcher(name=f"Prof {i}")
        service.provider.researchers.add(researcher)
        service.provider.researcher_campuses.upsert(researcher.id, campus.id)
        for y in range(3):
            article = Article(
                title=f"Art {i}-{y}", year=2020 + y, type=ArticleType.JOURNAL
            )
            service.provider.articles.add(article)
            article.authors = [researcher]
            service.provider.articles.update(article)
        researchers.append(researcher)
    service.provider.article_counts.rebuild()

    counts = []
    engine = service.provider.researchers._session_factory().get_bind()

    @event.listens_for(engine, "before_cursor_execute")
    def _count_statements(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
        counts.append(statement)

    service.get_profile(researchers[0].id, article_page=1, article_page_size=50)
    event.remove(engine, "before_cursor_execute", _count_statements)

    # researcher + campus + university + projects + counts + articles
    # (+ committed writes during setup are excluded) — bound at ~8 statements
    assert len(counts) <= 10, f"profile assembly issued {len(counts)} queries"


def test_directory_page_affiliation_lookup_is_batched(session_factory):
    service = ResearchDataService(session_factory)
    university = University(name="IFES", short_name="IFES")
    service.provider.universities.add(university)
    campus = Campus(name="Serra", organization_id=university.id)
    service.provider.campuses.add(campus)
    for i in range(25):
        researcher = Researcher(name=f"Docente {i}")
        service.provider.researchers.add(researcher)
        service.provider.researcher_campuses.upsert(researcher.id, campus.id)

    counts = []
    engine = service.provider.researchers._session_factory().get_bind()

    @event.listens_for(engine, "before_cursor_execute")
    def _count_statements(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
        counts.append(statement)

    items, total = service.search_professors("docente", page=1, page_size=25)
    event.remove(engine, "before_cursor_execute", _count_statements)

    assert total == 25
    assert all(i["affiliation"] == "Serra" for i in items)
    # search (1) + campus map (1) + campus names (1) + university lookup (1)
    assert len(counts) <= 5, f"directory lookup issued {len(counts)} queries"
