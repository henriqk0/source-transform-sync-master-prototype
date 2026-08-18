from datetime import UTC, datetime

import pytest
from research_domain.domain.entities import Researcher

from portal.ingestion.models import SyncState, SyncStateStatus
from portal.ingestion.repositories import SyncStateRepository
from portal.researchdata.models import ArticleCountByYear
from portal.researchdata.repositories import ArticleCountRepository


@pytest.fixture
def sync_repo(session_factory):
    return SyncStateRepository(session_factory)


class TestSyncStateModel:
    def test_default_status_is_idle(self, session_factory):
        repo = SyncStateRepository(session_factory)
        state = repo.get()
        assert state.status == SyncStateStatus.IDLE
        assert state.started_at is None
        assert state.finished_at is None
        assert state.counts is None

    def test_singleton_get_returns_same_row(self, session_factory):
        repo = SyncStateRepository(session_factory)
        first = repo.get()
        second = repo.get()
        assert first.id == second.id
        assert session_factory().query(SyncState).count() == 1

    def test_begin_to_success_transition(self, sync_repo):
        started = datetime.now(UTC).replace(tzinfo=None)
        sync_repo.begin()
        state = sync_repo.get()
        assert state.status == SyncStateStatus.RUNNING
        assert state.started_at is not None
        assert state.started_at >= started

        sync_repo.succeed({"researchers": 3, "articles": 10})
        state = sync_repo.get()
        assert state.status == SyncStateStatus.SUCCEEDED
        assert state.finished_at is not None
        assert state.counts == {"researchers": 3, "articles": 10}
        assert state.errors is None

    def test_begin_to_failure_transition(self, sync_repo):
        sync_repo.begin()
        sync_repo.fail([{"file": "articles.parquet", "detail": "bad row"}])
        state = sync_repo.get()
        assert state.status == SyncStateStatus.FAILED
        assert state.errors == [{"file": "articles.parquet", "detail": "bad row"}]

    def test_begin_while_running_rejected(self, sync_repo):
        sync_repo.begin()
        with pytest.raises(RuntimeError):
            sync_repo.begin()

    def test_reset_allows_reseed_after_terminal(self, sync_repo):
        sync_repo.begin()
        sync_repo.succeed({"researchers": 1})
        sync_repo.reset()
        state = sync_repo.get()
        assert state.status == SyncStateStatus.IDLE
        assert state.counts is None


class TestArticleCountByYearModel:
    def test_upsert_updates_existing_pair(self, session_factory):
        repo = ArticleCountRepository(session_factory)
        provider = __import__(
            "portal.researchdata.repositories", fromlist=["RepositoryProvider"]
        ).RepositoryProvider(session_factory)
        r = Researcher(name="Prof Contagens")
        provider.researchers.add(r)

        repo.upsert_counts([(r.id, 2023, 1)])
        repo.upsert_counts([(r.id, 2023, 2)])
        rows = session_factory().query(ArticleCountByYear).all()
        assert len(rows) == 1
        assert rows[0].count == 2
        assert rows[0].year == 2023

    def test_counts_ordered_most_recent_first(self, session_factory):
        repo = ArticleCountRepository(session_factory)
        provider = __import__(
            "portal.researchdata.repositories", fromlist=["RepositoryProvider"]
        ).RepositoryProvider(session_factory)
        r = Researcher(name="Prof Ordem")
        provider.researchers.add(r)

        repo.upsert_counts([(r.id, 2020, 1), (r.id, 2025, 9), (r.id, 2022, 3)])
        assert repo.counts_for_researcher(r.id) == [(2025, 9), (2022, 3), (2020, 1)]

    def test_rebuild_recomputes_from_article_authors(self, session_factory):
        repo = ArticleCountRepository(session_factory)
        provider = __import__(
            "portal.researchdata.repositories", fromlist=["RepositoryProvider"]
        ).RepositoryProvider(session_factory)
        from research_domain.domain.entities.article import Article, ArticleType

        r = Researcher(name="Prof Rebuild")
        provider.researchers.add(r)
        a1 = Article(title="X", year=2024, type=ArticleType.JOURNAL)
        a2 = Article(title="Y", year=2024, type=ArticleType.JOURNAL)
        a3 = Article(title="Z", year=2025, type=ArticleType.JOURNAL)
        provider.articles.add(a1)
        provider.articles.add(a2)
        provider.articles.add(a3)
        for art in [a1, a2, a3]:
            art.authors = [r]
            provider.articles.update(art)

        repo.upsert_counts([(r.id, 1999, 99)])
        repo.rebuild()
        assert repo.counts_for_researcher(r.id) == [(2025, 1), (2024, 2)]
