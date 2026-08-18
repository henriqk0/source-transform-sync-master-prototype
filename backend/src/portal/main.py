from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from portal.auth.controllers import create_auth_router, ensure_admin_bootstrap
from portal.config import Settings, load_settings
from portal.db import SessionFactory, create_session_factory, init_db
from portal.ingestion.controllers import create_ingestion_router
from portal.observability import install_masking
from portal.researchdata.controllers import create_researchdata_router
from portal.researchdata.services import ResearchDataService


def create_app(
    session_factory: SessionFactory | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    """Assemble the portal application (modular monolith, Art. I)."""
    settings = settings or load_settings()
    session_factory = session_factory or create_session_factory(settings.db_path)
    init_db(session_factory)
    install_masking()
    ensure_admin_bootstrap(session_factory, settings)

    app = FastAPI(title="Professor Data Portal", version="0.1.0")
    app.state.settings = settings
    app.state.session_factory = session_factory

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    research_service = ResearchDataService(session_factory)
    app.include_router(create_researchdata_router(research_service), prefix="/api")
    app.include_router(
        create_ingestion_router(session_factory, data_dir=settings.data_dir),
        prefix="/api",
    )
    app.include_router(create_auth_router(session_factory, settings), prefix="/api")

    return app
