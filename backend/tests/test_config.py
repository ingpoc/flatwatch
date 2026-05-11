import pytest

from app.config import get_runtime_mode, validate_runtime_security_config


def test_runtime_mode_normalizes_demo_staging_and_production(monkeypatch):
    monkeypatch.delenv("FLATWATCH_ENV", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    assert get_runtime_mode() == "demo"

    monkeypatch.setenv("FLATWATCH_ENV", "local")
    assert get_runtime_mode() == "demo"

    monkeypatch.setenv("FLATWATCH_ENV", "stage")
    assert get_runtime_mode() == "staging"

    monkeypatch.setenv("FLATWATCH_ENV", "prod")
    assert get_runtime_mode() == "production"


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
    monkeypatch.setenv("FLATWATCH_ALLOW_PRODUCTION_DEMO_AUTH", "true")
    monkeypatch.setenv("FLATWATCH_ALLOW_PRODUCTION_MOCK_RAZORPAY", "true")
    monkeypatch.setenv("FLATWATCH_ALLOW_PRODUCTION_MOCK_OCR", "true")

    validate_runtime_security_config()


def test_production_runtime_rejects_demo_and_mock_surfaces_without_explicit_allowances(monkeypatch):
    monkeypatch.setenv("FLATWATCH_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "flatwatch-production-secret-with-at-least-32-bytes")
    monkeypatch.setenv("ENCRYPTION_KEY", "flatwatch-production-encryption-key-32b")
    monkeypatch.delenv("FLATWATCH_ALLOW_PRODUCTION_DEMO_AUTH", raising=False)
    monkeypatch.delenv("FLATWATCH_ALLOW_PRODUCTION_MOCK_RAZORPAY", raising=False)
    monkeypatch.delenv("FLATWATCH_ALLOW_PRODUCTION_MOCK_OCR", raising=False)

    with pytest.raises(RuntimeError, match="FLATWATCH_ALLOW_PRODUCTION_DEMO_AUTH"):
        validate_runtime_security_config()


def test_staging_runtime_can_use_demo_defaults(monkeypatch):
    monkeypatch.setenv("FLATWATCH_ENV", "staging")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("FLATWATCH_ALLOW_PRODUCTION_DEMO_AUTH", raising=False)
    monkeypatch.delenv("FLATWATCH_ALLOW_PRODUCTION_MOCK_RAZORPAY", raising=False)
    monkeypatch.delenv("FLATWATCH_ALLOW_PRODUCTION_MOCK_OCR", raising=False)

    validate_runtime_security_config()
