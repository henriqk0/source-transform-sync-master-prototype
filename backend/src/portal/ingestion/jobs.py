"""Background seed job execution (async per Constitution Art. IV)."""

from __future__ import annotations

import threading

from portal.db import SessionFactory
from portal.ingestion.services import IngestionService


def run_seed_job(session_factory: SessionFactory, data_dir: str) -> None:
    """Execute the seed in a daemon thread; caller must have begun the state."""
    thread = threading.Thread(
        target=_seed_worker,
        args=(session_factory, data_dir),
        daemon=True,
        name="seed-job",
    )
    thread.start()


def _seed_worker(session_factory: SessionFactory, data_dir: str) -> None:
    try:
        IngestionService(session_factory, data_dir=data_dir).seed(
            check_running=False, begin_state=False
        )
    except Exception:
        # State transition to FAILED is handled inside service.seed().
        pass
