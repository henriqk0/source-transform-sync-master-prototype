"""SQLite concurrency regression tests (FR-014, FR-006).

Readers must never be blocked by an open writer transaction (WAL journal
mode); otherwise professor pages cannot render during a synchronization.
"""

import threading
import time

from sqlalchemy import text

from portal.db import create_session_factory, init_db

READ_BUDGET_S = 3.0


def test_readers_are_not_blocked_by_an_open_writer_transaction(tmp_path):
    factory = create_session_factory(str(tmp_path / "concurrent.db"))
    init_db(factory)

    inserted = threading.Event()
    released = threading.Event()

    def writer() -> None:
        session = factory()
        try:
            session.execute(text("PRAGMA cache_size=10"))
            session.execute(text("BEGIN IMMEDIATE"))
            for index in range(2000):
                session.execute(
                    text(
                        "INSERT INTO organizations (id, name, short_name) "
                        "VALUES (:id, :name, 'x')"
                    ),
                    {"id": 100000 + index, "name": f"holding-{index}"},
                )
            inserted.set()
            released.wait(timeout=10)
        finally:
            session.rollback()
            session.close()

    thread = threading.Thread(target=writer)
    thread.start()
    try:
        assert inserted.wait(timeout=10), "writer never opened its transaction"
        started = time.monotonic()
        reader = factory()
        try:
            count = reader.execute(
                text("SELECT COUNT(*) FROM organizations")
            ).scalar()
        finally:
            reader.close()
        elapsed = time.monotonic() - started
        assert count == 0, "uncommitted writer data must not be visible"
        assert elapsed < READ_BUDGET_S, (
            f"reader blocked {elapsed:.1f}s by an open writer transaction"
        )
    finally:
        released.set()
        thread.join()