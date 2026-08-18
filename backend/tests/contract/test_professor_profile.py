import pytest
from research_domain.domain.entities import Researcher

from portal.researchdata.services import ResearchDataService


@pytest.fixture
def service(session_factory):
    return ResearchDataService(session_factory)


def _make_client(app):
    from fastapi.testclient import TestClient

    return TestClient(app)


@pytest.fixture
def client(session_factory, app):
    service = ResearchDataService(session_factory)
    researcher = Researcher(name="Maria Alice Veiga Ferreira De Souza")
    service.provider.researchers.add(researcher)
    return _make_client(app), researcher.id


def test_get_profile_shape_and_hierarchy(client):
    http, researcher_id = client
    response = http.get(f"/api/professors/{researcher_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == researcher_id
    assert body["name"] == "Maria Alice Veiga Ferreira De Souza"
    for key in [
        "affiliation",
        "resume",
        "current_projects",
        "article_counts_by_year",
        "locations",
        "articles",
    ]:
        assert key in body
    assert body["current_projects"] == []
    assert body["article_counts_by_year"] == []
    assert body["locations"] == []
    assert body["articles"] == []


def test_get_profile_404(client):
    http, _ = client
    response = http.get("/api/professors/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Professor not found"


def test_get_profile_non_integer_422(client):
    http, _ = client
    response = http.get("/api/professors/abc")
    assert response.status_code == 422
