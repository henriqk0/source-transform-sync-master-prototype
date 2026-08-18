from __future__ import annotations

import enum

from eo_lib.domain.base import Base
from sqlalchemy import Boolean, Column, Enum, ForeignKey, Integer, String


class Role(enum.StrEnum):
    ADMIN = "ADMIN"
    PROFESSOR = "PROFESSOR"


class UserAccount(Base):
    """Portal-owned account (Auth module). NOT a canonical domain entity."""

    __tablename__ = "user_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(
        Enum(Role, values_callable=lambda e: [m.value for m in e]), nullable=False
    )
    researcher_id = Column(Integer, ForeignKey("researchers.id"), nullable=True)
    erased = Column(Boolean, default=False, nullable=False)

    def __init__(
        self,
        username: str,
        password_hash: str,
        role: Role,
        researcher_id: int | None = None,
        erased: bool = False,
        id: int | None = None,
    ) -> None:
        if not isinstance(role, Role):
            raise ValueError(f"invalid role: {role!r}")
        self.username = username
        self.password_hash = password_hash
        self.role = role
        self.researcher_id = researcher_id
        self.erased = erased
        if id:
            self.id = id
