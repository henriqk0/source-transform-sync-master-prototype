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
    from portal.config import load_settings
    from portal.main import create_app

    # Hermetic to every ambient config source (os.environ and the
    # backend/.env fallback): an explicit env dict makes load_settings
    # ignore both, so no ADMIN bootstrap can ever run during tests.
    settings = load_settings(env={"PORTAL_DATA_DIR": FIXTURES_DIR})
    return create_app(session_factory=session_factory, settings=settings)
