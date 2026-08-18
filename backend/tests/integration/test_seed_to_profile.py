"""T031 — seed → public profile cross-module integration (Ingestion → ResearchData)."""

from __future__ import annotations

import os

from fastapi.testclient import TestClient

from portal.ingestion.services import IngestionService

FIXTURES = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "fixtures", "seed"
)


def test_seed_then_profile_endpoint_serves_synced_data(session_factory, app):
    IngestionService(session_factory, data_dir=FIXTURES).seed()

    client = TestClient(app)
    profile = client.get("/api/professors/1").json()
    assert profile["name"] == "Maria Alice Veiga Ferreira De Souza"
    assert profile["affiliation"] == "Vila Velha"
    assert [p["name"] for p in profile["current_projects"]] == ["Projeto X"]
    assert profile["article_counts_by_year"] == [
        {"year": 2025, "count": 1},
        {"year": 2024, "count": 1},
    ]
    assert [a["title"] for a in profile["articles"]] == [
        "Publicacao A",
        "Publicacao B",
    ]


def test_seed_then_directory_search_finds_professors(session_factory, app):
    IngestionService(session_factory, data_dir=FIXTURES).seed()
    client = TestClient(app)
    body = client.get("/api/professors?q=joao").json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Joao da Silva"
