from __future__ import annotations

from sqlalchemy.orm import Session

from portal.auth.models import Role, UserAccount
from portal.db import SessionFactory


class AuthRepository:
    """SQLite repository for portal-owned user accounts."""

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def _session(self) -> Session:
        return self._session_factory()

    def add(self, account: UserAccount) -> None:
        if account.role == Role.PROFESSOR and account.researcher_id is None:
            raise ValueError("PROFESSOR account must reference an existing Researcher")
        session = self._session()
        try:
            session.add(account)
            session.commit()
            session.refresh(account)
        finally:
            session.close()

    def get_by_id(self, account_id: int) -> UserAccount | None:
        session = self._session()
        try:
            return session.get(UserAccount, account_id)
        finally:
            session.close()

    def get_by_username(self, username: str) -> UserAccount | None:
        session = self._session()
        try:
            return (
                session.query(UserAccount)
                .filter(UserAccount.username == username)
                .first()
            )
        finally:
            session.close()

    def get_all(self) -> list[UserAccount]:
        session = self._session()
        try:
            return session.query(UserAccount).all()
        finally:
            session.close()

    def is_erased(self, researcher_id: int) -> bool:
        session = self._session()
        try:
            account = (
                session.query(UserAccount)
                .filter(UserAccount.researcher_id == researcher_id)
                .first()
            )
            return account is not None and account.erased
        finally:
            session.close()

    def update(self, account: UserAccount) -> None:
        session = self._session()
        try:
            session.merge(account)
            session.commit()
        finally:
            session.close()

    def delete(self, account_id: int) -> None:
        session = self._session()
        try:
            account = session.get(UserAccount, account_id)
            if account:
                session.delete(account)
                session.commit()
        finally:
            session.close()
