from __future__ import annotations

from collections.abc import Callable

from eo_lib.domain.base import Base
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, scoped_session, sessionmaker

SessionFactory = Callable[[], Session]


def create_session_factory(db_path: str) -> SessionFactory:
    """Create a session factory bound to a SQLite file database.

    All tables (canonical research_domain entities + portal-owned models)
    live on the shared eo_lib ``Base.metadata`` and are created by
    :func:`init_db`.
    """
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _configure_sqlite(dbapi_connection, _connection_record):  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        # WAL keeps readers on the last committed snapshot while a long
        # writer transaction (e.g. seed) runs, per FR-014/FR-006.
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

    factory = scoped_session(
        sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
            expire_on_commit=False,
        )
    )
    factory.engine = engine  # type: ignore[attr-defined]
    return factory


def init_db(factory: SessionFactory) -> None:
    """Create all tables (canonical + portal-owned) on the database.

    Portal-owned modules are imported here so their tables are always
    registered on ``Base.metadata`` regardless of the import path that
    reaches this function.
    """
    import portal.auth.models  # noqa: F401
    import portal.ingestion.models  # noqa: F401
    import portal.researchdata.models  # noqa: F401

    Base.metadata.create_all(factory().get_bind())
