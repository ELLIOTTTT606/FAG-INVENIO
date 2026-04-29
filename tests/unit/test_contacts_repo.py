"""Tests for the contacts repository (Mock + Baserow impl)."""

from __future__ import annotations

import httpx

from src.services.baserow_client import BaserowClient, BaserowConfig
from src.services.contacts_repo import (
    BaserowContactsRepository,
    BaserowTables,
    Client,
    Contact,
    ContactsForDepartment,
    MockContactsRepository,
)


def test_mock_search_requires_at_least_two_characters() -> None:
    repo = MockContactsRepository()
    assert repo.search_clients("") == []
    assert repo.search_clients("L") == []
    assert repo.search_clients("Ly")


def test_mock_search_matches_name_code_and_postal_code() -> None:
    repo = MockContactsRepository()
    by_name = repo.search_clients("hopital")
    assert any("Hôpital" in c.client_name for c in by_name)

    by_code = repo.search_clients("c310")
    assert [c.client_code for c in by_code] == ["C310"]

    by_postal = repo.search_clients("75015")
    assert [c.postal_code for c in by_postal] == ["75015"]


def test_mock_get_contacts_known_department_returns_full_set() -> None:
    repo = MockContactsRepository()
    result = repo.get_contacts_for_department("69")
    assert result.tci is not None and "Camille" in (result.tci.name or "")
    assert result.tcs is not None
    assert result.solution is not None


def test_mock_get_contacts_unknown_department_keeps_solution_only() -> None:
    repo = MockContactsRepository()
    result = repo.get_contacts_for_department("88")
    assert result.tci is None
    assert result.tcs is None
    assert result.solution is not None


def _baserow_client(transport: httpx.MockTransport) -> BaserowClient:
    config = BaserowConfig(base_url="https://baserow.test", token="dummy")
    return BaserowClient(
        config,
        client=httpx.Client(
            base_url=config.base_url, headers=config.headers, transport=transport
        ),
    )


def test_baserow_repo_searches_clients_via_iter_all_rows() -> None:
    rows = [
        {"client_code": "A1", "client_name": "Acme Health", "postal_code": "75000", "department": "75"},
        {"client_code": "B2", "client_name": "Beta Lyon", "postal_code": "69001", "department": "69"},
    ]

    def handle(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": rows, "next": None})

    repo = BaserowContactsRepository(
        client=_baserow_client(httpx.MockTransport(handle)),
        tables=BaserowTables(clients=10, contacts_force_vente=20, contacts_solution=30),
    )
    matches = repo.search_clients("lyon")
    assert [c.client_code for c in matches] == ["B2"]


def test_baserow_repo_resolves_department_contacts() -> None:
    fv_rows = [
        {
            "departments": "69, 01",
            "tci_name": "Camille",
            "tci_email": "c@x.com",
            "tci_phone": "0472001234",
            "tcs_name": "Paul",
            "tcs_email": "p@x.com",
            "tcs_phone": "0472001235",
        }
    ]
    sol_rows = [{"name": "Solution", "email": "sh@x.com", "phone": "01"}]

    def handle(request: httpx.Request) -> httpx.Response:
        if "/table/20/" in str(request.url):
            return httpx.Response(200, json={"results": fv_rows, "next": None})
        if "/table/30/" in str(request.url):
            return httpx.Response(200, json={"results": sol_rows, "next": None})
        return httpx.Response(200, json={"results": [], "next": None})

    repo = BaserowContactsRepository(
        client=_baserow_client(httpx.MockTransport(handle)),
        tables=BaserowTables(clients=10, contacts_force_vente=20, contacts_solution=30),
    )
    result = repo.get_contacts_for_department("69")
    assert result.tci == Contact("Camille", "c@x.com", "0472001234")
    assert result.tcs == Contact("Paul", "p@x.com", "0472001235")
    assert result.solution and result.solution.name == "Solution"


def test_contacts_for_department_to_dict_serializes_nones() -> None:
    payload = ContactsForDepartment(department="42", tci=None, tcs=None, solution=None).to_dict()
    assert payload == {"department": "42", "tci": None, "tcs": None, "solution": None}


def test_client_to_dict_round_trip() -> None:
    client = Client("C1", "Foo", "75001", "75")
    assert client.to_dict() == {
        "client_code": "C1",
        "client_name": "Foo",
        "postal_code": "75001",
        "department": "75",
    }
