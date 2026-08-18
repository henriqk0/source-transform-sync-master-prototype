"""Auth service: credential verification and JWT issuance/verification."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from portal.auth.models import UserAccount
from portal.auth.repositories import AuthRepository
from portal.db import SessionFactory


class AuthService:
    def __init__(
        self,
        session_factory: SessionFactory,
        jwt_secret: str,
        jwt_expires_minutes: int = 120,
    ) -> None:
        self._session_factory = session_factory
        self._jwt_secret = jwt_secret
        self._jwt_expires_minutes = jwt_expires_minutes
        self._repository = AuthRepository(session_factory)

    def authenticate(self, username: str, password: str) -> UserAccount | None:
        user = self._repository.get_by_username(username)
        if user is None or user.erased:
            return None
        if not bcrypt.checkpw(
            password.encode("utf-8"), user.password_hash.encode("utf-8")
        ):
            return None
        return user

    def create_token(self, user: UserAccount) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": user.username,
            "role": user.role.value,
            "researcher_id": user.researcher_id,
            "iat": now,
            "exp": now + timedelta(minutes=self._jwt_expires_minutes),
        }
        return jwt.encode(payload, self._jwt_secret, algorithm="HS256")

    def verify_token(self, token: str) -> dict:
        return jwt.decode(token, self._jwt_secret, algorithms=["HS256"])
