"""Tests for src.services.settings."""

from __future__ import annotations

import pytest

from src.services.settings import (
    Settings,
    is_live_baserow_test_enabled,
    reload_settings,
)


@pytest.fixture(autouse=True)
def _clear_baserow_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in [
        "BASEROW_URL",
        "BASEROW_TOKEN",
        "BASEROW_TIMEOUT",
        "BASEROW_MAX_RETRIES",
        "BASEROW_CACHE_TTL",
        "BASEROW_TABLE_CLIENTS",
        "BASEROW_TABLE_CONTACTS_FORCE_VENTE",
        "BASEROW_TABLE_CONTACTS_SOLUTION",
        "BASEROW_TABLE_OPTIONS_ACCESSOIRES",
        "BASEROW_TABLE_DESIGNATION_DECODER",
        "INVENIO_BASEROW_LIVE",
    ]:
        monkeypatch.delenv(key, raising=False)


def test_settings_default_to_mock_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir("/tmp")  # avoid picking up the repo .env
    settings = reload_settings()
    assert settings.baserow_live is False
    assert settings.baserow_mode == "mock"


def test_settings_promote_to_live_when_url_and_token_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BASEROW_URL", "https://baserow.test")
    monkeypatch.setenv("BASEROW_TOKEN", "abc")
    monkeypatch.setenv("BASEROW_TABLE_CLIENTS", "12")
    settings = reload_settings()
    assert settings.baserow_live is True
    assert settings.baserow_mode == "live"
    assert settings.baserow_table_clients == 12


def test_settings_validates_retry_bounds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BASEROW_MAX_RETRIES", "999")
    with pytest.raises(Exception):  # noqa: B017 - pydantic ValidationError
        Settings()  # type: ignore[call-arg]


def test_is_live_baserow_test_enabled_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    assert is_live_baserow_test_enabled() is False
    monkeypatch.setenv("INVENIO_BASEROW_LIVE", "1")
    assert is_live_baserow_test_enabled() is True
