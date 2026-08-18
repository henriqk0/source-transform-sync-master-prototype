from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from portal.auth.dependencies import require_admin
from portal.db import SessionFactory
from portal.ingestion.jobs import run_seed_job
from portal.ingestion.repositories import SyncStateRepository
from portal.ingestion.services import (
    DatabaseNotEmpty,
    IngestionService,
    SeedAlreadyRunning,
)


def create_ingestion_router(
    session_factory: SessionFactory, data_dir: str
) -> APIRouter:
    router = APIRouter(tags=["admin"])
    service = IngestionService(session_factory, data_dir=data_dir)
    sync_states = SyncStateRepository(session_factory)

    @router.post("/admin/seed", dependencies=[Depends(require_admin)], status_code=202)
    def trigger_seed(request: Request) -> dict:
        try:
            service._ensure_empty()
        except SeedAlreadyRunning:
            raise HTTPException(
                status_code=400, detail="Seed already running"
            ) from None
        except DatabaseNotEmpty:
            raise HTTPException(
                status_code=409, detail="Database already seeded"
            ) from None

        sync_states.begin()
        run_seed_job(request.app.state.session_factory, data_dir)
        state = sync_states.get()
        return {
            "status": state.status.value,
            "started_at": state.started_at.isoformat(),
        }

    @router.get("/admin/sync-status", dependencies=[Depends(require_admin)])
    def sync_status() -> dict:
        return sync_states.get_state_dict()

    return router
