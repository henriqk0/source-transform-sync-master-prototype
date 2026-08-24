import os

import pytest

from portal.db import create_session_factory, init_db

FIXTURES_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "fixtures", "seed"
)


@pytest.fixture
def session_factory(tmp_path):
    """Real SQLite file database per test (Constitution Art. II)."""
    db_path = tmp_path / "portal-test.db"
    factory = create_session_factory(str(db_path))
    init_db(factory)
    yield factory
    session = factory()
    try:
        session.close()
    finally:
        engine = factory.__self__ if hasattr(factory, "__self__") else None
        if engine is not None:
            engine.dispose()


@pytest.fixture
def app(session_factory, monkeypatch):
    """FastAPI application wired to the per-test session factory."""
    from portal.main import create_app

    # Hermetic to ambient env (backend/.env leaks via research_domain/eo_lib
    # import-time load_dotenv): never bootstrap the ADMIN account in tests.
    monkeypatch.delenv("ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    monkeypatch.setenv("PORTAL_DATA_DIR", FIXTURES_DIR)
    return create_app(session_factory=session_factory)
