"""Tests for Settings fail-fast validation (RC1 Phase 0 — Security
Remediation, Findings 2, 7, 8).

Settings() reads from the process environment plus backend/.env
(app/config.py). To test "missing/invalid value fails startup" without
disturbing the real, already-imported app.config.settings singleton or the
real backend/.env file, these tests construct a fresh Settings instance
directly with `_env_file=None` (so it never reads backend/.env) and
explicitly clear the relevant environment variables first (so a real
developer's shell environment can never make these tests flaky), driving
every input through explicit constructor kwargs.
"""
import pytest
from pydantic import ValidationError

from app.config import Settings, resolve_debug_setting


def _clear_env(monkeypatch):
    for name in ("DATABASE_URL", "SESSION_SECRET", "ENVIRONMENT", "DEBUG"):
        monkeypatch.delenv(name, raising=False)


def _settings(monkeypatch, **overrides):
    _clear_env(monkeypatch)
    base = {
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/testdb",
        "SESSION_SECRET": "a" * 32,
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)


class TestSessionSecretFailFast:
    def test_missing_session_secret_fails(self, monkeypatch):
        _clear_env(monkeypatch)
        with pytest.raises(ValidationError):
            Settings(_env_file=None, DATABASE_URL="postgresql://x/y")

    def test_empty_session_secret_fails(self, monkeypatch):
        with pytest.raises(ValidationError):
            _settings(monkeypatch, SESSION_SECRET="")

    def test_whitespace_only_session_secret_fails(self, monkeypatch):
        with pytest.raises(ValidationError):
            _settings(monkeypatch, SESSION_SECRET="   ")

    def test_known_weak_fallback_literal_is_gone_from_launch_scripts(self, monkeypatch):
        """'dev-secret' is a syntactically valid non-empty string, so
        Settings' own validator cannot reject it as a *value* -- any
        non-empty string is a legal secret. The actual fix is that no
        launch path supplies this literal as a fallback anymore (see
        backend/run_server.py and scripts/dev-backend.mjs, both of which
        now fail fast instead of defaulting to it)."""
        s = _settings(monkeypatch, SESSION_SECRET="dev-secret")
        assert s.SESSION_SECRET == "dev-secret"  # Settings accepts any non-empty string...

        # ...but the dangerous *fallback pattern* is gone from every launch
        # script (explanatory comments may still mention the old literal by
        # name, so check for the executable pattern, not the bare word).
        import inspect
        import run_server
        source = inspect.getsource(run_server)
        assert "setdefault('SESSION_SECRET'" not in source
        assert "setdefault(\"SESSION_SECRET\"" not in source

        import pathlib
        dev_backend_mjs = pathlib.Path(__file__).resolve().parent.parent.parent / "scripts" / "dev-backend.mjs"
        assert "|| 'dev-secret'" not in dev_backend_mjs.read_text(encoding="utf-8")

    def test_explicit_strong_secret_starts_successfully(self, monkeypatch):
        s = _settings(monkeypatch, SESSION_SECRET="a-sufficiently-long-random-secret-value")
        assert s.SESSION_SECRET == "a-sufficiently-long-random-secret-value"
        assert s.SECRET_KEY == s.SESSION_SECRET


class TestDatabaseUrlFailFast:
    def test_missing_database_url_fails(self, monkeypatch):
        _clear_env(monkeypatch)
        with pytest.raises(ValidationError):
            Settings(_env_file=None, SESSION_SECRET="a" * 32)

    def test_empty_database_url_fails(self, monkeypatch):
        with pytest.raises(ValidationError):
            _settings(monkeypatch, DATABASE_URL="")

    def test_error_output_contains_no_credentials(self, monkeypatch):
        with pytest.raises(ValidationError) as exc_info:
            _settings(monkeypatch, DATABASE_URL="")
        message = str(exc_info.value)
        # the old insecure hardcoded fallback value must never appear in
        # any error text, and no other DB credential does either
        assert "user:password@localhost" not in message
        assert "Admin123" not in message

    def test_explicit_database_url_loads(self, monkeypatch):
        s = _settings(monkeypatch, DATABASE_URL="postgresql://someuser:somepass@dbhost:5432/somedb")
        assert s.DATABASE_URL == "postgresql://someuser:somepass@dbhost:5432/somedb"

    def test_no_hardcoded_default_value_on_the_field(self, monkeypatch):
        """A field with a hardcoded default would still construct
        successfully even with DATABASE_URL cleared from the environment
        -- assert that is no longer the case."""
        _clear_env(monkeypatch)
        with pytest.raises(ValidationError):
            Settings(_env_file=None, SESSION_SECRET="a" * 32)


class TestDebugProductionGuard:
    def test_debug_true_in_production_is_rejected(self):
        with pytest.raises(RuntimeError):
            resolve_debug_setting(True, "production")

    def test_debug_true_in_staging_is_rejected(self):
        with pytest.raises(RuntimeError):
            resolve_debug_setting(True, "staging")

    def test_debug_true_in_development_is_allowed(self):
        assert resolve_debug_setting(True, "development") is True

    def test_debug_false_is_always_allowed(self):
        assert resolve_debug_setting(False, "production") is False
        assert resolve_debug_setting(False, "staging") is False
        assert resolve_debug_setting(False, "development") is False

    def test_default_debug_value_is_false(self, monkeypatch):
        s = _settings(monkeypatch)
        assert s.DEBUG is False

    def test_settings_module_import_did_not_raise(self):
        """The real app.config module (backed by the real backend/.env,
        which has ENVIRONMENT=development / DEBUG=true) must import
        cleanly -- this is what actually gates the real application's
        startup, exercised on every test run via conftest.py's own
        `from app.config import settings`."""
        from app.config import settings
        assert settings.ENVIRONMENT is not None
