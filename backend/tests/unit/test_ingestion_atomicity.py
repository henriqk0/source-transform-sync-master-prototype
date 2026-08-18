"""T028 — seed atomicity, deduplication, and FR-021 read-only sources."""

from __future__ import annotations

import hashlib
import os
import shutil

import pyarrow
import pytest
from sqlalchemy import text

from portal.ingestion.models import SyncState
from portal.ingestion.services import IngestionService
from portal.researchdata.repositories import RepositoryProvider

FIXTURES = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "fixtures", "seed"
)


@pytest.fixture
def broken_data_dir(tmp_path) -> str:
    target = tmp_path / "broken"
    shutil.copytree(FIXTURES, target)
    # Corrupt the articles file: invalid parquet bytes.
    (target / "articles_canonical.parquet").write_bytes(b"not a parquet file")
    return str(target)


def _fingerprint(data_dir: str) -> dict[str, tuple[str, int]]:
    result = {}
    for name in sorted(os.listdir(data_dir)):
        path = os.path.join(data_dir, name)
        if os.path.isfile(path):
            with open(path, "rb") as handle:
                result[name] = (
                    hashlib.sha256(handle.read()).hexdigest(),
                    os.path.getmtime(path),
                )
    return result


def test_failure_leaves_database_untouched(session_factory, broken_data_dir):
    service = IngestionService(session_factory, data_dir=broken_data_dir)
    with pytest.raises(pyarrow.lib.ArrowInvalid):
        service.seed()
    provider = RepositoryProvider(session_factory)
    assert len(provider.researchers.get_all()) == 0
    assert len(provider.articles.get_all()) == 0
    assert len(provider.initiatives.get_all()) == 0
    status = service.sync_status()
    assert status["status"] == "FAILED"
    assert status["counts"] is None
    assert status["errors"] is not None
    assert len(status["errors"]) == 1
    assert status["errors"][0]["file"] == "articles_canonical.parquet"


def test_failed_seed_allows_retry_after_fix(session_factory, broken_data_dir):
    service = IngestionService(session_factory, data_dir=broken_data_dir)
    with pytest.raises(pyarrow.lib.ArrowInvalid):
        service.seed()
    with pytest.raises(pyarrow.lib.ArrowInvalid):
        service.seed()  # must not be stuck in RUNNING


def test_source_files_never_written_fr021(session_factory, tmp_path):
    target = tmp_path / "copy"
    shutil.copytree(FIXTURES, target)
    before = _fingerprint(str(target))
    service = IngestionService(session_factory, data_dir=str(target))
    service.seed()
    after = _fingerprint(str(target))
    assert before == after


def test_success_then_wiped_db_reseeds_with_same_counts(session_factory):
    first = IngestionService(session_factory, data_dir=FIXTURES)
    first.seed()
    first_counts = first.sync_status()["counts"]

    provider = RepositoryProvider(session_factory)
    session = session_factory()
    session.execute(text("PRAGMA foreign_keys=OFF"))
    from portal.researchdata.models import ArticleCountByYear, ResearcherCampus

    for entity in [
        provider.researchers._entity_type,
        provider.articles._entity_type,
        provider.initiatives._entity_type,
        ResearcherCampus,
        ArticleCountByYear,
        provider.campuses._entity_type,
        provider.universities._entity_type,
        provider.areas._entity_type,
        provider.production_types._entity_type,
        provider.productions._entity_type,
        provider.advisorships._entity_type,
        provider.fellowships._entity_type,
        provider.groups._entity_type,
        SyncState,
    ]:
        session.execute(text(f'DELETE FROM "{entity.__tablename__}"'))
    session.execute(text('DELETE FROM "teams"'))
    session.execute(text('DELETE FROM "persons"'))
    session.execute(text('DELETE FROM "initiative_persons"'))
    session.execute(text('DELETE FROM "article_authors"'))
    session.execute(text("PRAGMA foreign_keys=ON"))
    session.commit()
    session.close()

    second = IngestionService(session_factory, data_dir=FIXTURES)
    second.seed()
    second_counts = second.sync_status()["counts"]
    assert second_counts == first_counts


def test_masked_error_detail_on_failure(session_factory, broken_data_dir):
    service = IngestionService(session_factory, data_dir=broken_data_dir)
    with pytest.raises(pyarrow.lib.ArrowInvalid):
        service.seed()
    status = service.sync_status()
    assert status["errors"] is not None
    for error in status["errors"]:
        detail = error["detail"].lower()
        assert "email" not in detail
        assert "lgpd-" not in detail
