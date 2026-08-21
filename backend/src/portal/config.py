from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


def load_dotenv_file(path: Path) -> dict[str, str]:
    """Minimal .env loader: KEY=VALUE lines, comments and blanks ignored,
    optional surrounding quotes stripped. os.environ takes precedence."""
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def _effective_env(env: dict[str, str] | None) -> dict[str, str]:
    """os.environ values win; otherwise fall back to backend/.env."""
    if env is None:
        return {**load_dotenv_file(BACKEND_DIR / ".env"), **os.environ}
    return env


@dataclass(frozen=True)
class Settings:
    db_path: str
    jwt_secret: str
    jwt_expires_minutes: int
    admin_username: str | None
    admin_password: str | None
    data_dir: str


def load_settings(env: dict[str, str] | None = None) -> Settings:
    env = _effective_env(env)
    return Settings(
        db_path=env.get("PORTAL_DB_PATH", str(BACKEND_DIR / "portal.db")),
        jwt_secret=env.get("PORTAL_JWT_SECRET", "dev-secret-change-me"),
        jwt_expires_minutes=int(env.get("PORTAL_JWT_EXPIRES_MINUTES", "60")),
        admin_username=env.get("ADMIN_USERNAME"),
        admin_password=env.get("ADMIN_PASSWORD"),
        data_dir=env.get("PORTAL_DATA_DIR", str(BACKEND_DIR / "data")),
    )


def load_admin_credentials(env: dict[str, str] | None = None) -> tuple[str, str] | None:
    env = _effective_env(env)
    username = env.get("ADMIN_USERNAME")
    password = env.get("ADMIN_PASSWORD")
    if username and password:
        return username, password
    return None
