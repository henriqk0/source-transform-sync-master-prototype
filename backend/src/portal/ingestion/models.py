from __future__ import annotations

import enum
import json
from datetime import UTC, datetime

from eo_lib.domain.base import Base
from sqlalchemy import Column, DateTime, Enum, Integer, Text


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class SyncStateStatus(enum.StrEnum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class SyncState(Base):
    """Portal-owned synchronization state (Ingestion module)."""

    __tablename__ = "sync_state"

    id = Column(Integer, primary_key=True, default=1)
    status = Column(
        Enum(SyncStateStatus, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=SyncStateStatus.IDLE,
    )
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    counts_json = Column(Text, nullable=True)
    errors_json = Column(Text, nullable=True)

    @property
    def counts(self) -> dict | None:
        return json.loads(self.counts_json) if self.counts_json else None

    @property
    def errors(self) -> list | None:
        return json.loads(self.errors_json) if self.errors_json else None
