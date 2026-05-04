"""Tests for tools.baserow_smoke (mocked Baserow)."""

from __future__ import annotations

import httpx
import pytest

from src.services.settings import Settings
from tools import baserow_smoke


@pytest.fixture()
def settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    for key in [
        "BASEROW_URL",
        "BASEROW_TOKEN",
        "BASEROW_TABLE_CLIENTS",
        "BASEROW_TABLE_CONTACTS_FORCE_VENTE",
        "BASEROW_TABLE_CONTACTS_SOLUTION",
        "BASEROW_TABLE_OPTIONS_ACCESSOIRES",
    ]:
        monkeypatch.delenv(key, raising=False)
    return Settings(
        BASEROW_URL="https://baserow.test",
        BASEROW_TOKEN="dummy",
        BASEROW_TABLE_CLIENTS=10,
        BASEROW_TABLE_CONTACTS_FORCE_VENTE=20,
        BASEROW_TABLE_CONTACTS_SOLUTION=30,
        BASEROW_TABLE_OPTIONS_ACCESSOIRES=40,
    )


def _install_transport(monkeypatch: pytest.MonkeyPatch, handler: httpx.MockTransport) -> None:
    """Patch BaserowClient so it uses our MockTransport."""

    from src.services import baserow_client as bc_mod

    real_init = bc_mod.BaserowClient.__init__

    def patched_init(self, config, *, client=None, sleep=None):  # type: ignore[no-untyped-def]
        if client is None:
            client = httpx.Client(
                base_url=config.base_url,
                headers=config.headers,
                transport=handler,
            )
        real_init(self, config, client=client, sleep=sleep or (lambda _: None))

    monkeypatch.setattr(bc_mod.BaserowClient, "__init__", patched_init)


def test_run_probes_reports_all_ok_on_happy_path(
    monkeypatch: pytest.MonkeyPatch, settings: Settings
) -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "/tokens/check/" in url:
            return httpx.Response(200, json={"ok": True})
        if "/table/10/" in url:
            return httpx.Response(
                200,
                json={
                    "count": 1,
                    "results": [
                        {
                            "client_name": "Acme Lyon",
                            "client_code": "C1",
                            "department": "69",
                            "postal_code": "69001",
                        }
                    ],
                    "next": None,
                },
            )
        if "/table/20/" in url:
            return httpx.Response(
                200,
                json={
                    "count": 1,
                    "results": [
                        {
                            "departments": "69",
                            "tci_name": "Camille",
                            "tci_email": "c@x.com",
                            "tci_phone": "0",
                            "tcs_name": "Paul",
                            "tcs_email": "p@x.com",
                            "tcs_phone": "0",
                        }
                    ],
                    "next": None,
                },
            )
        if "/table/30/" in url:
            return httpx.Response(
                200,
                json={
                    "count": 1,
                    "results": [{"name": "Solutions", "email": "s@x.com", "phone": "0"}],
                    "next": None,
                },
            )
        if "/table/40/" in url:
            return httpx.Response(
                200,
                json={
                    "count": 1,
                    "results": [
                        {
                            "model": "PLP",
                            "type": "HS",
                            "size": "052",
                            "option_code": "P",
                            "option_category": "Kit antigel",
                            "label_fr": "Protection",
                        }
                    ],
                    "next": None,
                },
            )
        return httpx.Response(404, text="not found")

    _install_transport(monkeypatch, httpx.MockTransport(handle))
    results = baserow_smoke.run_probes(
        settings,
        sample_query="lyon",
        sample_department="69",
        sample_model="PLP",
        sample_type="HS",
        sample_size="052",
    )
    assert all(r.ok for r in results), [
        (r.name, r.message) for r in results if not r.ok
    ]
    names = {r.name for r in results}
    assert {
        "auth",
        "table.CLIENTS",
        "table.contacts_force_vente",
        "table.contacts_solution",
        "table.options_accessoires",
        "search_clients",
        "contacts_for_department",
        "list_options",
    } <= names


def test_run_probes_flags_missing_config() -> None:
    settings = Settings(BASEROW_URL="", BASEROW_TOKEN="")
    results = baserow_smoke.run_probes(
        settings,
        sample_query="x",
        sample_department="69",
        sample_model="PLP",
        sample_type="HS",
        sample_size="052",
    )
    assert results == [
        baserow_smoke.ProbeResult(
            name="config",
            ok=False,
            message="BASEROW_URL/BASEROW_TOKEN missing; cannot probe",
            details={"baserow_url": False, "baserow_token": False},
        )
    ]


def test_run_probes_marks_failing_table(
    monkeypatch: pytest.MonkeyPatch, settings: Settings
) -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        if "/tokens/check/" in str(request.url):
            return httpx.Response(200, json={"ok": True})
        if "/table/10/" in str(request.url):
            return httpx.Response(403, text="forbidden")
        return httpx.Response(200, json={"results": [], "next": None})

    _install_transport(monkeypatch, httpx.MockTransport(handle))
    results = baserow_smoke.run_probes(
        settings,
        sample_query="lyon",
        sample_department="69",
        sample_model="PLP",
        sample_type="HS",
        sample_size="052",
    )
    by_name = {r.name: r for r in results}
    assert by_name["table.CLIENTS"].ok is False
