"""Project-wide pytest configuration."""

from __future__ import annotations

import pytest

from src.services.settings import is_live_baserow_test_enabled


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Skip `live` tests unless `INVENIO_BASEROW_LIVE=1` is set."""

    del config  # only here to satisfy the pytest hook signature
    if is_live_baserow_test_enabled():
        return
    skip_live = pytest.mark.skip(reason="set INVENIO_BASEROW_LIVE=1 to run live Baserow tests")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)
