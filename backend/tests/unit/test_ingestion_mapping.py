"""T027 — parquet → canonical entity mapping (data-model.md section 6)."""

from __future__ import annotations

import os

import pytest
from research_domain.domain.entities import Campus, University
from research_domain.domain.entities.article import ArticleType

from portal.ingestion.repositories import SyncStateRepository
from portal.ingestion.services import IngestionService
from portal.researchdata.repositories import RepositoryProvider
from portal.researchdata.services import ResearchDataService

FIXTURES = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "fixtures", "seed"
)


@pytest.fixture
def seeded(session_factory):
    service = IngestionService(session_factory, data_dir=FIXTURES)
    service.seed()
    return service


def test_researchers_mapped_with_campus_and_resume(session_factory, seeded):
    provider = RepositoryProvider(session_factory)
    researcher = provider.researchers.get_by_id(1)
    assert researcher.name == "Maria Alice Veiga Ferreira De Souza"
    assert researcher.resume == "Professora titular"
    assert provider.researcher_campuses.campus_id_for(1) == 1
    assert provider.researchers.get_by_id(2).name == "Joao da Silva"


def test_lattes_id_extracted_from_cnpq_url_for_linking(session_factory, seeded):
    provider = RepositoryProvider(session_factory)
    assert provider.researcher_cnpqs.researcher_for("1111222233334444") == 1
    # Researchers without a cnpq_url get no mapping.
    assert provider.researcher_cnpqs.researcher_for("9999999999999999") is None


def test_articles_mapped_with_authors_and_counts(session_factory, seeded):
    provider = RepositoryProvider(session_factory)
    article = provider.articles.get_by_id(100)
    assert article.title == "Publicacao A"
    assert article.year == 2025
    assert article.type == ArticleType.JOURNAL
    assert [a.id for a in article.authors] == [1]
    article_b = provider.articles.get_by_id(101)
    assert article_b.type == ArticleType.CONFERENCE_EVENT
    counts = provider.article_counts.counts_for_researcher(1)
    assert sorted(counts) == [(2024, 1), (2025, 1)]


def test_article_type_mapping_is_case_insensitive(session_factory, seeded):
    provider = RepositoryProvider(session_factory)
    assert provider.articles.get_by_id(100).type == ArticleType.JOURNAL
    assert provider.articles.get_by_id(101).type == ArticleType.CONFERENCE_EVENT


def test_initiative_status_mapping_and_team_links(session_factory, seeded):
    provider = RepositoryProvider(session_factory)
    current = provider.initiatives.list_active_for_researcher(1)
    assert [i.id for i in current] == [10]
    assert provider.initiatives.get_by_id(10).name == "Projeto X"


def test_dangling_person_ref_recorded_as_error_but_professor_published(
    session_factory, seeded
):
    provider = RepositoryProvider(session_factory)
    assert provider.initiatives.get_by_id(11) is not None
    assert provider.researchers.get_by_id(1) is not None
    assert provider.researchers.get_by_id(2) is not None

    status_repo = SyncStateRepository(session_factory)
    status = status_repo.get()
    assert status.status.value == "SUCCEEDED"
    details = [e["detail"] for e in status.errors]
    assert any("999" in detail for detail in details)
    assert all(e["file"] == "initiatives_canonical.parquet" for e in status.errors)
    assert all(e["record"] == "11" for e in status.errors)


def test_organizations_mapped_with_first_as_university(session_factory, seeded):
    provider = RepositoryProvider(session_factory)
    university = provider.universities.get_by_id(1)
    assert isinstance(university, University)
    assert university.name == "Instituto Federal do Espirito Santo"
    campus = provider.campuses.get_by_id(1)
    assert isinstance(campus, Campus)
    assert campus.name == "Vila Velha"


def test_seed_counts_shape(session_factory, seeded):
    status = seeded.sync_status()
    expected_keys = {
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
    }
    assert expected_keys <= set(status["counts"])
    assert status["counts"]["researchers"] == 2
    assert status["counts"]["articles"] == 2
    assert status["counts"]["initiatives"] == 2
    assert status["counts"]["campuses"] == 2
    assert status["counts"]["research_productions"] == 1


def test_seeded_data_queryable_through_researchdata(session_factory, seeded):
    service = ResearchDataService(session_factory)
    profile = service.get_profile(1)
    assert profile["name"] == "Maria Alice Veiga Ferreira De Souza"
    assert profile["affiliation"] == "Vila Velha"
    assert [p["name"] for p in profile["current_projects"]] == ["Projeto X"]
    assert profile["article_counts_by_year"] == [
        {"year": 2025, "count": 1},
        {"year": 2024, "count": 1},
    ]


def test_deduplication_across_reloads(session_factory):
    first = IngestionService(session_factory, data_dir=FIXTURES)
    first.seed()
    second = IngestionService(session_factory, data_dir=FIXTURES)
    with pytest.raises(RuntimeError):
        second.seed()
    provider = RepositoryProvider(session_factory)
    assert len(provider.researchers.get_all()) == 2
    assert len(provider.articles.get_all()) == 2
