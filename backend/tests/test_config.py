import pytest

from app.config import validate_runtime_security_config


def test_production_runtime_rejects_missing_security_secrets(monkeypatch):
    monkeypatch.setenv("FLATWATCH_ENV", "production")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)

    with pytest.raises(RuntimeError, match="SECRET_KEY, ENCRYPTION_KEY"):
        validate_runtime_security_config()


def test_production_runtime_accepts_non_default_security_secrets(monkeypatch):
    monkeypatch.setenv("FLATWATCH_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "flatwatch-production-secret-with-at-least-32-bytes")
    monkeypatch.setenv("ENCRYPTION_KEY", "flatwatch-production-encryption-key-32b")

    validate_runtime_security_config()
