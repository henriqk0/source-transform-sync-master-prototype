"""Auth HTTP controllers: login and current-user endpoints."""

from __future__ import annotations

import bcrypt
from fastapi import APIRouter, Depends, Form, HTTPException, Response

from portal.auth.dependencies import get_current_user
from portal.auth.models import Role, UserAccount
from portal.auth.repositories import AuthRepository
from portal.auth.services import AuthService
from portal.config import Settings
from portal.db import SessionFactory


def ensure_admin_bootstrap(session_factory: SessionFactory, settings: Settings) -> None:
    """Create the ADMIN account from env credentials if configured (startup)."""
    if not settings.admin_username or not settings.admin_password:
        return
    repository = AuthRepository(session_factory)
    if repository.get_by_username(settings.admin_username) is not None:
        return
    repository.add(
        UserAccount(
            username=settings.admin_username,
            password_hash=bcrypt.hashpw(
                settings.admin_password.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8"),
            role=Role.ADMIN,
        )
    )


def create_auth_router(
    session_factory: SessionFactory, settings: Settings
) -> APIRouter:
    service = AuthService(
        session_factory,
        jwt_secret=settings.jwt_secret,
        jwt_expires_minutes=settings.jwt_expires_minutes,
    )
    router = APIRouter(prefix="/auth", tags=["auth"])

    @router.post("/login")
    def login(
        response: Response,
        username: str = Form(...),
        password: str = Form(...),
    ) -> dict:
        user = service.authenticate(username, password)
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        return {
            "access_token": service.create_token(user),
            "token_type": "bearer",
            "role": user.role.value,
            "researcher_id": user.researcher_id,
        }

    @router.get("/me")
    def me(user: UserAccount = Depends(get_current_user)) -> dict:
        return {
            "id": user.id,
            "username": user.username,
            "role": user.role.value,
            "researcher_id": user.researcher_id,
        }

    return router
