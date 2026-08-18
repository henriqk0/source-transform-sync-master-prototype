import pytest
from eo_lib.domain.entities import Initiative
from research_domain.domain.entities import Campus, Researcher, University
from research_domain.domain.entities.article import Article, ArticleType

from portal.researchdata.services import ResearchDataService


@pytest.fixture
def service(session_factory):
    return ResearchDataService(session_factory)


def _seed_profile_data(service):
    """Researcher with projects, counts, campus, and articles."""
    university = University(
        name="Instituto Federal do Espirito Santo", short_name="IFES"
    )
    service.provider.universities.add(university)
    campus = Campus(name="Vila Velha", organization_id=university.id)
    service.provider.campuses.add(campus)

    researcher = Researcher(name="Maria Alice Veiga Ferreira De Souza")
    service.provider.researchers.add(researcher)
    service.provider.researcher_campuses.upsert(researcher.id, campus.id)

    active = Initiative(name="Projeto Ativo", status="Active")
    old = Initiative(name="Projeto Antigo", status="Concluded")
    service.provider.initiatives.add(active)
    service.provider.initiatives.add(old)
    service.provider.initiatives.add_person(active.id, researcher.id)
    service.provider.initiatives.add_person(old.id, researcher.id)

    for year, count in [(2024, 2), (2025, 5)]:
        for _ in range(count):
            article = Article(
                title=f"Art {year}-{_}", year=year, type=ArticleType.JOURNAL
            )
            service.provider.articles.add(article)
            article.authors = [researcher]
            service.provider.articles.update(article)
    service.provider.article_counts.rebuild()
    return researcher, campus, university


class TestProfileAssembly:
    def test_full_profile_hierarchy_order(self, service):
        researcher, campus, university = _seed_profile_data(service)
        profile = service.get_profile(researcher.id)

        assert profile["id"] == researcher.id
        assert profile["name"] == "Maria Alice Veiga Ferreira De Souza"
        assert profile["affiliation"] == "Vila Velha"
        assert [p["name"] for p in profile["current_projects"]] == ["Projeto Ativo"]
        assert profile["current_projects"][0]["status"] == "Active"
        assert profile["article_counts_by_year"] == [
            {"year": 2025, "count": 5},
            {"year": 2024, "count": 2},
        ]
        assert {"id": campus.id, "name": "Vila Velha", "type": "campus"} in profile[
            "locations"
        ]
        assert {
            "id": university.id,
            "name": "Instituto Federal do Espirito Santo",
            "type": "organization",
        } in profile["locations"]
        assert len(profile["articles"]) == 7
        assert profile["articles_total"] == 7

    def test_empty_sections_are_empty_lists(self, service):
        researcher = Researcher(name="Prof Sem Dados")
        service.provider.researchers.add(researcher)
        profile = service.get_profile(researcher.id)
        assert profile["current_projects"] == []
        assert profile["article_counts_by_year"] == []
        assert profile["locations"] == []
        assert profile["articles"] == []
        assert profile["affiliation"] is None

    def test_articles_ordered_most_recent_first_and_paginated(self, service):
        researcher = Researcher(name="Prof Paginação")
        service.provider.researchers.add(researcher)
        for i in range(9):
            article = Article(
                title=f"Paper {i}",
                year=2015 + i,
                type=ArticleType.JOURNAL if i % 2 else ArticleType.CONFERENCE_EVENT,
            )
            service.provider.articles.add(article)
            article.authors = [researcher]
            service.provider.articles.update(article)
        service.provider.article_counts.rebuild()

        page1 = service.get_profile(researcher.id, article_page=1, article_page_size=4)
        page2 = service.get_profile(researcher.id, article_page=2, article_page_size=4)
        assert [a["year"] for a in page1["articles"]] == [2023, 2022, 2021, 2020]
        assert [a["year"] for a in page2["articles"]] == [2019, 2018, 2017, 2016]
        assert page1["articles_total"] == 9

    def test_unknown_researcher_raises(self, service):
        with pytest.raises(KeyError):
            service.get_profile(9999)


class TestSearch:
    def test_fragment_search(self, service):
        for name in ["Carlos Roberto Pires Campos", "Carlos Alberto", "Joao"]:
            service.provider.researchers.add(Researcher(name=name))
        items, total = service.search_professors("carlos", page=1, page_size=10)
        assert total == 2
        assert all("carlos" in i["name"].lower() for i in items)

    def test_no_query_returns_all(self, service):
        service.provider.researchers.add(Researcher(name="A"))
        service.provider.researchers.add(Researcher(name="B"))
        items, total = service.search_professors(None, page=1, page_size=20)
        assert total == 2
        assert {i["name"] for i in items} == {"A", "B"}

    def test_empty_result(self, service):
        items, total = service.search_professors("zzz", page=1, page_size=20)
        assert items == []
        assert total == 0
