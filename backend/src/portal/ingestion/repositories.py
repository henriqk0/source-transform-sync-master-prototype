from __future__ import annotations

import json

from sqlalchemy.orm import Session

from portal.db import SessionFactory
from portal.ingestion.models import SyncState, SyncStateStatus, utcnow


class SyncStateRepository:
    """Single-row state machine: IDLE -> RUNNING -> SUCCEEDED/FAILED."""

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def get(self) -> SyncState:
        session = self._session()
        try:
            state = session.query(SyncState).first()
            if state is None:
                state = SyncState(status=SyncStateStatus.IDLE)
                session.add(state)
                session.commit()
                session.refresh(state)
            return state
        finally:
            session.close()

    def begin(self) -> SyncState:
        session = self._session()
        try:
            state = session.query(SyncState).first()
            if state is None:
                state = SyncState(status=SyncStateStatus.IDLE)
                session.add(state)
            if state.status == SyncStateStatus.RUNNING:
                raise RuntimeError("Seed already running")
            state.status = SyncStateStatus.RUNNING
            state.started_at = utcnow()
            state.finished_at = None
            state.counts_json = None
            state.errors_json = None
            session.commit()
            session.refresh(state)
            return state
        finally:
            session.close()

    def succeed(self, counts: dict, errors: list[dict] | None = None) -> SyncState:
        session = self._session()
        try:
            state = session.query(SyncState).first()
            if state is None:
                raise RuntimeError("No sync state")
            state.status = SyncStateStatus.SUCCEEDED
            state.finished_at = utcnow()
            state.counts_json = json.dumps(counts)
            state.errors_json = json.dumps(errors) if errors else None
            session.commit()
            session.refresh(state)
            return state
        finally:
            session.close()

    def fail(self, errors: list[dict]) -> SyncState:
        session = self._session()
        try:
            state = session.query(SyncState).first()
            if state is None:
                raise RuntimeError("No sync state")
            state.status = SyncStateStatus.FAILED
            state.finished_at = utcnow()
            state.errors_json = json.dumps(errors)
            session.commit()
            session.refresh(state)
            return state
        finally:
            session.close()

    def reset(self) -> SyncState:
        session = self._session()
        try:
            state = session.query(SyncState).first()
            if state is None:
                state = SyncState(status=SyncStateStatus.IDLE)
                session.add(state)
            state.status = SyncStateStatus.IDLE
            state.started_at = None
            state.finished_at = None
            state.counts_json = None
            state.errors_json = None
            session.commit()
            session.refresh(state)
            return state
        finally:
            session.close()

    def get_state_dict(self) -> dict:
        state = self.get()
        return {
            "status": state.status.value,
            "started_at": state.started_at.isoformat() if state.started_at else None,
            "finished_at": state.finished_at.isoformat() if state.finished_at else None,
            "counts": state.counts,
            "errors": state.errors,
        }

    def _session(self) -> Session:
        return self._session_factory()
