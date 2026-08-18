import pytest
from research_domain.domain.entities import Researcher

from portal.researchdata.services import ResearchDataService


@pytest.fixture
def http(session_factory, app):
    from fastapi.testclient import TestClient

    service = ResearchDataService(session_factory)
    for name in [
        "Carlos Roberto Pires Campos",
        "Carlos Alberto",
        "Maria Alice Veiga Ferreira De Souza",
    ]:
        service.provider.researchers.add(Researcher(name=name))
    return TestClient(app)


def test_list_pagination_shape(http):
    response = http.get("/api/professors?page=1&page_size=2")
    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert body["total"] == 3
    assert len(body["items"]) == 2
    for item in body["items"]:
        assert set(item.keys()) == {"id", "name", "affiliation"}


def test_list_page_size_bounds(http):
    assert http.get("/api/professors?page_size=0").status_code == 422
    assert http.get("/api/professors?page_size=101").status_code == 422
    assert http.get("/api/professors?page=0").status_code == 422
    assert http.get("/api/professors?page=-1").status_code == 422


def test_search_q_filters_and_paginates(http):
    page1 = http.get("/api/professors?q=carlos&page=1&page_size=1").json()
    assert page1["total"] == 2
    assert len(page1["items"]) == 1
    assert "carlos" in page1["items"][0]["name"].lower()

    page2 = http.get("/api/professors?q=carlos&page=2&page_size=1").json()
    assert len(page2["items"]) == 1
    assert page2["items"][0]["name"] != page1["items"][0]["name"]


def test_search_no_matches(http):
    body = http.get("/api/professors?q=zzz").json()
    assert body["total"] == 0
    assert body["items"] == []


def test_search_case_insensitive(http):
    body = http.get("/api/professors?q=MARIA").json()
    assert body["total"] == 1
