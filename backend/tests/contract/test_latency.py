"""T057 — latency regression gates (Art. IV, SC-006).

Pages: p95 < 2s. Search: p95 < 5s. Measured on the fixture dataset with
repeated calls through the full HTTP stack (TestClient).
"""

from __future__ import annotations

import statistics
import time

import pytest
from fastapi.testclient import TestClient

from portal.ingestion.services import IngestionService

FIXTURES = __import__("os").path.join(
    __import__("os").path.dirname(__file__), "..", "fixtures", "seed"
)

SAMPLES = 30


@pytest.fixture
def client(session_factory, app) -> TestClient:
    IngestionService(session_factory, data_dir=FIXTURES).seed()
    return TestClient(app)


def _measure(client: TestClient, path: str, n: int = SAMPLES) -> list[float]:
    samples: list[float] = []
    for _ in range(n):
        started = time.perf_counter()
        response = client.get(path)
        elapsed = (time.perf_counter() - started) * 1000
        assert response.status_code == 200
        samples.append(elapsed)
    return samples


def _p95(samples: list[float]) -> float:
    return statistics.quantiles(samples, n=100)[94]


def test_professor_page_latency_budget(session_factory, client):
    samples = _measure(client, "/api/professors/1")
    assert _p95(samples) < 2000, f"p95 profile latency {_p95(samples):.0f}ms > 2s"


def test_search_latency_budget(session_factory, client):
    samples = _measure(client, "/api/professors?q=a&page=1&page_size=50")
    assert _p95(samples) < 5000, f"p95 search latency {_p95(samples):.0f}ms > 5s"


def test_directory_list_latency_budget(session_factory, client):
    samples = _measure(client, "/api/professors?page=1&page_size=20")
    assert _p95(samples) < 2000, f"p95 list latency {_p95(samples):.0f}ms > 2s"
