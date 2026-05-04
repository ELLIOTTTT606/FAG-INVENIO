"""Contract tests against a real Baserow instance.

These run only when `INVENIO_BASEROW_LIVE=1` is exported. They expect the
canonical FA tables to be reachable via the env-configured token. The
tests are read-only and safe to run against production.
"""

from __future__ import annotations

import pytest

from src.services.settings import get_settings, reload_settings
from tools.baserow_smoke import run_probes

pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def settings():
    return reload_settings()


def test_baserow_is_configured(settings) -> None:  # type: ignore[no-untyped-def]
    assert settings.baserow_live, (
        "Set BASEROW_URL and BASEROW_TOKEN before running live tests."
    )


def test_smoke_probes_are_all_green(settings) -> None:  # type: ignore[no-untyped-def]
    results = run_probes(
        settings,
        sample_query="a",
        sample_department="69",
        sample_model="PLP",
        sample_type="HS",
        sample_size="052",
    )
    failed = [(r.name, r.message) for r in results if not r.ok]
    assert not failed, f"failed probes: {failed}"


def test_get_settings_singleton_is_live() -> None:
    assert get_settings().baserow_live is True
