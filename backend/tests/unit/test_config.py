from __future__ import annotations

import pytest

from portal import config


@pytest.fixture
def env_dir(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(config, "BACKEND_DIR", tmp_path)


def _write_env(tmp_path, lines: list[str]) -> None:
    (tmp_path / ".env").write_text("\n".join(lines), encoding="utf-8")


def test_env_file_values_used_when_not_in_os_environ(env_dir, tmp_path, monkeypatch):
    _write_env(
        tmp_path,
        [
            "PORTAL_DB_PATH=/from/envfile.db",
            'PORTAL_JWT_SECRET="envfile-secret"',
            "ADMIN_USERNAME=envfile-admin",
        ],
    )
    monkeypatch.delenv("PORTAL_DB_PATH", raising=False)
    monkeypatch.delenv("PORTAL_JWT_SECRET", raising=False)
    monkeypatch.delenv("ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)

    settings = config.load_settings()

    assert settings.db_path == "/from/envfile.db"
    assert settings.jwt_secret == "envfile-secret"
    assert settings.admin_username == "envfile-admin"


def test_os_environ_takes_precedence_over_env_file(env_dir, tmp_path, monkeypatch):
    _write_env(tmp_path, ["PORTAL_DB_PATH=/from/envfile.db"])
    monkeypatch.setenv("PORTAL_DB_PATH", "/from/os.environ.db")

    settings = config.load_settings()

    assert settings.db_path == "/from/os.environ.db"


def test_missing_env_file_uses_defaults(env_dir, tmp_path, monkeypatch):
    for key in (
        "PORTAL_DB_PATH",
        "PORTAL_JWT_SECRET",
        "ADMIN_USERNAME",
        "ADMIN_PASSWORD",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = config.load_settings()

    assert settings.db_path == str(tmp_path / "portal.db")
    assert settings.jwt_secret == "dev-secret-change-me"
    assert settings.admin_username is None


def test_export_prefix_and_comments_are_handled(env_dir, tmp_path, monkeypatch):
    _write_env(
        tmp_path,
        [
            "# a comment",
            "",
            "export PORTAL_JWT_SECRET=exported-secret",
            "PORTAL_JWT_EXPIRES_MINUTES=30",
        ],
    )
    monkeypatch.delenv("PORTAL_JWT_SECRET", raising=False)
    monkeypatch.delenv("PORTAL_JWT_EXPIRES_MINUTES", raising=False)

    settings = config.load_settings()

    assert settings.jwt_secret == "exported-secret"
    assert settings.jwt_expires_minutes == 30


def test_admin_credentials_fall_back_to_env_file(env_dir, tmp_path, monkeypatch):
    _write_env(
        tmp_path, ["ADMIN_USERNAME=envfile-admin", "ADMIN_PASSWORD=envfile-pass"]
    )
    monkeypatch.delenv("ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)

    assert config.load_admin_credentials() == ("envfile-admin", "envfile-pass")


def test_os_environ_wins_for_admin_credentials(env_dir, tmp_path, monkeypatch):
    _write_env(
        tmp_path, ["ADMIN_USERNAME=envfile-admin", "ADMIN_PASSWORD=envfile-pass"]
    )
    monkeypatch.setenv("ADMIN_USERNAME", "real-admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "real-pass")

    assert config.load_admin_credentials() == ("real-admin", "real-pass")


def test_ignores_malformed_lines(env_dir, tmp_path, monkeypatch):
    _write_env(tmp_path, ["NOT_A_KEY_VALUE", "=orphan", "KEY", "  "])
    monkeypatch.delenv("PORTAL_DB_PATH", raising=False)

    settings = config.load_settings()

    assert settings.db_path == str(tmp_path / "portal.db")
