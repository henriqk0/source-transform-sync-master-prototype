import pytest
from eo_lib.domain.entities import Initiative
from research_domain.domain.entities import (
    Advisorship,
    Campus,
    Fellowship,
    KnowledgeArea,
    Researcher,
    ResearchGroup,
    ResearchProduction,
    University,
)
from research_domain.domain.entities.article import Article, ArticleType

from portal.researchdata.repositories import (
    RepositoryProvider,
)


@pytest.fixture
def provider(session_factory):
    return RepositoryProvider(session_factory)


class TestSQLiteResearcherRepository:
    def test_crud_against_real_sqlite_file(self, provider):
        repo = provider.researchers
        researcher = Researcher(name="Maria Alice Veiga Ferreira De Souza")
        repo.add(researcher)
        assert researcher.id is not None

        loaded = repo.get_by_id(researcher.id)
        assert loaded is not None
        assert loaded.name == "Maria Alice Veiga Ferreira De Souza"

        loaded.name = "Maria Alice V. F. De Souza"
        repo.update(loaded)
        assert repo.get_by_id(researcher.id).name == "Maria Alice V. F. De Souza"

        repo.delete(researcher.id)
        assert repo.get_by_id(researcher.id) is None

    def test_get_all_returns_all(self, provider):
        repo = provider.researchers
        repo.add(Researcher(name="A"))
        repo.add(Researcher(name="B"))
        assert {r.name for r in repo.get_all()} == {"A", "B"}

    def test_search_by_name_fragment(self, provider):
        repo = provider.researchers
        for name in ["Carlos Roberto Pires Campos", "Carlos Alberto", "Joao"]:
            repo.add(Researcher(name=name))
        items, total = repo.search("carlos", page=1, page_size=10)
        assert total == 2
        assert {i.name for i in items} == {
            "Carlos Roberto Pires Campos",
            "Carlos Alberto",
        }

    def test_search_pagination(self, provider):
        repo = provider.researchers
        for i in range(25):
            repo.add(Researcher(name=f"Prof #{i:02d}"))
        page1, total = repo.search("prof", page=1, page_size=20)
        page2, _ = repo.search("prof", page=2, page_size=20)
        assert total == 25
        assert len(page1) == 20
        assert len(page2) == 5


class TestSQLiteArticleRepository:
    def test_find_by_title_year(self, provider):
        repo = provider.articles
        repo.add(Article(title="MTS-PolKA", year=2025, type=ArticleType.JOURNAL))
        found = repo.find_by_title_year("MTS-PolKA", 2025)
        assert found is not None
        assert repo.find_by_title_year("MTS-PolKA", 2024) is None

    def test_find_by_doi(self, provider):
        repo = provider.articles
        repo.add(
            Article(
                title="T",
                year=2025,
                type=ArticleType.CONFERENCE_EVENT,
                doi="10.1234/x",
            )
        )
        assert repo.find_by_doi("10.1234/x") is not None
        assert repo.find_by_doi("missing") is None

    def test_list_by_year(self, provider):
        repo = provider.articles
        repo.add(Article(title="A1", year=2024, type=ArticleType.JOURNAL))
        repo.add(Article(title="A2", year=2024, type=ArticleType.JOURNAL))
        repo.add(Article(title="A3", year=2025, type=ArticleType.JOURNAL))
        assert len(repo.list_by_year(2024)) == 2

    def test_list_for_researcher_paginated(self, provider):
        articles = provider.articles
        researcher = provider.researchers
        r = Researcher(name="Dra. Pesquisadora")
        researcher.add(r)
        for i in range(7):
            articles.add(
                Article(title=f"Art {i}", year=2020 + i, type=ArticleType.JOURNAL)
            )
        for art in articles.get_all():
            art.authors = [r]
            articles.update(art)
        items, total = articles.list_for_researcher(r.id, page=1, page_size=5)
        assert total == 7
        assert len(items) == 5
        assert items[0].title == "Art 6"
        items2, _ = articles.list_for_researcher(r.id, page=2, page_size=5)
        assert len(items2) == 2


class TestSQLiteInitiativeRepository:
    def test_list_active_for_researcher(self, provider):
        researchers = provider.researchers
        initiatives = provider.initiatives
        r = Researcher(name="Prof Ativa")
        researchers.add(r)
        active = Initiative(name="Projeto Ativo", status="Active")
        concluded = Initiative(name="Projeto Antigo", status="Concluded")
        other = Initiative(name="Projeto De Outro", status="Active")
        initiatives.add(active)
        initiatives.add(concluded)
        initiatives.add(other)
        initiatives.add_person(active.id, r.id)
        initiatives.add_person(concluded.id, r.id)

        result = initiatives.list_active_for_researcher(r.id)
        assert [i.name for i in result] == ["Projeto Ativo"]
        assert result[0].status == "Active"


class TestOtherRepositories:
    def test_university_campus_group_area(self, provider):
        university = provider.universities
        campus = provider.campuses
        groups = provider.groups
        areas = provider.areas

        org = University(name="Instituto Federal do Espirito Santo", short_name="IFES")
        university.add(org)
        camp = Campus(name="Vila Velha", organization_id=org.id)
        campus.add(camp)
        assert campus.get_by_id(camp.id).name == "Vila Velha"

        group = ResearchGroup(name="Grupo X", campus_id=camp.id, organization_id=org.id)
        groups.add(group)
        assert groups.get_all()[0].campus_id == camp.id

        area = KnowledgeArea(name="Computação")
        areas.add(area)
        assert areas.find_by_name("computação") is not None

    def test_advisorship_fellowship_production(self, provider):
        adv = provider.advisorships
        fel = provider.fellowships
        prod = provider.productions
        types = provider.production_types

        from research_domain.domain.entities import ProductionType

        book = ProductionType(name="Book")
        types.add(book)

        fellowship = Fellowship(name="Bolsa IC", value=400.0)
        fel.add(fellowship)
        assert fel.get_by_id(fellowship.id).value == 400.0

        advisorship = Advisorship(name="IC 2025", status="Active")
        adv.add(advisorship)
        assert adv.get_by_id(advisorship.id).name == "IC 2025"

        production = ResearchProduction(
            title="Livro", year=2024, production_type_id=book.id
        )
        prod.add(production)
        assert prod.get_by_id(production.id).title == "Livro"


class TestArticleCountRepository:
    def test_upsert_and_ordering(self, provider):
        repo = provider.article_counts
        researcher = provider.researchers
        r = Researcher(name="Prof Artigos")
        researcher.add(r)

        repo.upsert_counts([(r.id, 2024, 2), (r.id, 2025, 5)])
        repo.upsert_counts([(r.id, 2024, 3)])
        counts = repo.counts_for_researcher(r.id)
        assert counts == [(2025, 5), (2024, 3)]

    def test_delete_for_researcher(self, provider):
        repo = provider.article_counts
        researcher = provider.researchers
        r = Researcher(name="Prof Limpeza")
        researcher.add(r)
        repo.upsert_counts([(r.id, 2024, 1)])
        repo.delete_for_researcher(r.id)
        assert repo.counts_for_researcher(r.id) == []
