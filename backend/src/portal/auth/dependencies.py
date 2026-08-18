"""FastAPI dependencies: current-user resolution and role guards."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from portal.auth.models import Role, UserAccount
from portal.auth.repositories import AuthRepository

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> UserAccount:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    settings = request.app.state.settings
    from portal.auth.services import AuthService

    service = AuthService(
        request.app.state.session_factory,
        jwt_secret=settings.jwt_secret,
        jwt_expires_minutes=settings.jwt_expires_minutes,
    )
    try:
        claims = service.verify_token(credentials.credentials)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    user = AuthRepository(request.app.state.session_factory).get_by_username(
        claims.get("sub", "")
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_admin(user: UserAccount = Depends(get_current_user)) -> UserAccount:
    if user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )
    return user
