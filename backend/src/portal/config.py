from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


@dataclass(frozen=True)
class Settings:
    db_path: str
    jwt_secret: str
    jwt_expires_minutes: int
    admin_username: str | None
    admin_password: str | None
    data_dir: str


def load_settings(env: dict[str, str] | None = None) -> Settings:
    env = os.environ if env is None else env
    return Settings(
        db_path=env.get("PORTAL_DB_PATH", str(BACKEND_DIR / "portal.db")),
        jwt_secret=env.get("PORTAL_JWT_SECRET", "dev-secret-change-me"),
        jwt_expires_minutes=int(env.get("PORTAL_JWT_EXPIRES_MINUTES", "60")),
        admin_username=env.get("ADMIN_USERNAME"),
        admin_password=env.get("ADMIN_PASSWORD"),
        data_dir=env.get("PORTAL_DATA_DIR", str(BACKEND_DIR / "data")),
    )


def load_admin_credentials(env: dict[str, str] | None = None) -> tuple[str, str] | None:
    env = os.environ if env is None else env
    username = env.get("ADMIN_USERNAME")
    password = env.get("ADMIN_PASSWORD")
    if username and password:
        return username, password
    return None
