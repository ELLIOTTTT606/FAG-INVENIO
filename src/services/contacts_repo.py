"""Repository abstraction for clients & department contacts.

Two implementations:
  - `MockContactsRepository` ships with a small but plausible dataset so
    the UI works in dev without Baserow credentials.
  - `BaserowContactsRepository` queries the real Baserow tables (CLIENTS,
    Contacts FORCE DE VENTE, Contacts SOLUTION) using the `BaserowClient`.

The FastAPI app picks the implementation in `make_repository_from_env()`
based on the `BASEROW_TOKEN` env variable; routes depend on the abstract
type.
"""

from __future__ import annotations

import os
import unicodedata
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from src.services.baserow_client import BaserowClient, BaserowConfig


def _fold(value: str) -> str:
    """Lowercase + strip accents for accent-insensitive matching."""

    return "".join(
        c for c in unicodedata.normalize("NFKD", value.lower()) if not unicodedata.combining(c)
    )


@dataclass(frozen=True)
class Contact:
    name: str | None = None
    email: str | None = None
    phone: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {"name": self.name, "email": self.email, "phone": self.phone}


@dataclass(frozen=True)
class Client:
    client_code: str
    client_name: str
    postal_code: str
    department: str

    def to_dict(self) -> dict[str, str]:
        return {
            "client_code": self.client_code,
            "client_name": self.client_name,
            "postal_code": self.postal_code,
            "department": self.department,
        }


@dataclass(frozen=True)
class ContactsForDepartment:
    department: str
    tci: Contact | None = None
    tcs: Contact | None = None
    solution: Contact | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "department": self.department,
            "tci": self.tci.to_dict() if self.tci else None,
            "tcs": self.tcs.to_dict() if self.tcs else None,
            "solution": self.solution.to_dict() if self.solution else None,
        }


class ContactsRepository(ABC):
    @abstractmethod
    def search_clients(self, query: str, limit: int = 10) -> list[Client]: ...

    @abstractmethod
    def get_contacts_for_department(self, department: str) -> ContactsForDepartment: ...


# ---------------------------------------------------------------------------
# Mock implementation (used in dev / when BASEROW_TOKEN is not set)
# ---------------------------------------------------------------------------

_MOCK_CLIENTS: tuple[Client, ...] = (
    Client("C123", "Société Lyon Immobilier", "69001", "69"),
    Client("C124", "Hôpital Edouard Herriot", "69003", "69"),
    Client("C201", "Mairie de Marseille", "13001", "13"),
    Client("C202", "Aéroport de Marseille Provence", "13727", "13"),
    Client("C310", "Tour Montparnasse", "75015", "75"),
    Client("C311", "Hôtel de Ville de Paris", "75004", "75"),
    Client("C420", "Centre Hospitalier de Bordeaux", "33000", "33"),
    Client("C530", "Crédit Agricole - Toulouse", "31000", "31"),
    Client("C600", "Polyclinique de Strasbourg", "67000", "67"),
    Client("C710", "Auchan Lille Villeneuve", "59650", "59"),
)

_MOCK_DEPARTMENT_CONTACTS: dict[str, ContactsForDepartment] = {
    "69": ContactsForDepartment(
        department="69",
        tci=Contact("Camille Durand", "c.durand@france-air.com", "04 72 00 12 34"),
        tcs=Contact("Paul Lefevre", "p.lefevre@france-air.com", "04 72 00 12 35"),
        solution=Contact("Solutions Habitat", "solutions.habitat@france-air.com", "04 48 40 40 40"),
    ),
    "13": ContactsForDepartment(
        department="13",
        tci=Contact("Léa Martin", "l.martin@france-air.com", "04 91 10 20 30"),
        tcs=Contact("Marc Bernard", "m.bernard@france-air.com", "04 91 10 20 31"),
        solution=Contact("Solutions Habitat", "solutions.habitat@france-air.com", "04 48 40 40 40"),
    ),
    "75": ContactsForDepartment(
        department="75",
        tci=Contact("Sophie Petit", "s.petit@france-air.com", "01 40 20 30 40"),
        tcs=Contact("Julien Roux", "j.roux@france-air.com", "01 40 20 30 41"),
        solution=Contact("Solutions Habitat", "solutions.habitat@france-air.com", "04 48 40 40 40"),
    ),
}


class MockContactsRepository(ContactsRepository):
    """In-memory repository with a small but realistic dataset."""

    def __init__(
        self,
        clients: tuple[Client, ...] = _MOCK_CLIENTS,
        contacts: dict[str, ContactsForDepartment] | None = None,
    ) -> None:
        self._clients = clients
        self._contacts = contacts if contacts is not None else _MOCK_DEPARTMENT_CONTACTS

    def search_clients(self, query: str, limit: int = 10) -> list[Client]:
        normalized = _fold((query or "").strip())
        if len(normalized) < 2:
            return []
        matches = [
            c
            for c in self._clients
            if normalized in _fold(c.client_name)
            or normalized in _fold(c.client_code)
            or normalized in c.postal_code
        ]
        return matches[: max(1, limit)]

    def get_contacts_for_department(self, department: str) -> ContactsForDepartment:
        if department in self._contacts:
            return self._contacts[department]
        return ContactsForDepartment(
            department=department,
            tci=None,
            tcs=None,
            solution=Contact(
                "Solutions Habitat",
                "solutions.habitat@france-air.com",
                "04 48 40 40 40",
            ),
        )


# ---------------------------------------------------------------------------
# Baserow-backed implementation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BaserowTables:
    clients: int
    contacts_force_vente: int
    contacts_solution: int


def _first_str(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value:
            return str(value).strip()
    return ""


def _row_to_client(row: dict[str, Any]) -> Client | None:
    name = _first_str(row, "client_name", "Nom", "name")
    if not name:
        return None
    return Client(
        client_code=_first_str(row, "client_code", "Code", "code"),
        client_name=name,
        postal_code=_first_str(row, "postal_code", "Code postal", "cp"),
        department=_first_str(row, "department", "department_code", "Departement"),
    )


def _row_to_contact(row: dict[str, Any], prefix: str = "") -> Contact | None:
    name = _first_str(row, f"{prefix}name", "name", "Nom") if prefix else _first_str(
        row, "name", "Nom"
    )
    email = _first_str(row, f"{prefix}email", "email", "Email") if prefix else _first_str(
        row, "email", "Email"
    )
    phone = _first_str(row, f"{prefix}phone", "phone", "Telephone") if prefix else _first_str(
        row, "phone", "Telephone"
    )
    if not (name or email or phone):
        return None
    return Contact(name=name or None, email=email or None, phone=phone or None)


class BaserowContactsRepository(ContactsRepository):
    """Reads CLIENTS, Contacts FORCE DE VENTE, Contacts SOLUTION."""

    def __init__(self, client: BaserowClient, tables: BaserowTables) -> None:
        self._client = client
        self._tables = tables

    def search_clients(self, query: str, limit: int = 10) -> list[Client]:
        normalized = _fold((query or "").strip())
        if len(normalized) < 2:
            return []
        matches: list[Client] = []
        for row in self._client.iter_all_rows(self._tables.clients):
            client = _row_to_client(row)
            if client is None:
                continue
            haystack = (
                _fold(client.client_name)
                + " "
                + _fold(client.client_code)
                + " "
                + client.postal_code
            )
            if normalized in haystack:
                matches.append(client)
                if len(matches) >= limit:
                    break
        return matches

    def get_contacts_for_department(self, department: str) -> ContactsForDepartment:
        tci: Contact | None = None
        tcs: Contact | None = None
        for row in self._client.iter_all_rows(self._tables.contacts_force_vente):
            departments = str(row.get("departments") or row.get("Departements") or "")
            if department not in {d.strip() for d in departments.split(",")}:
                continue
            tci = tci or _row_to_contact(row, prefix="tci_")
            tcs = tcs or _row_to_contact(row, prefix="tcs_")
            if tci and tcs:
                break

        solution: Contact | None = None
        for row in self._client.iter_all_rows(self._tables.contacts_solution):
            solution = _row_to_contact(row)
            if solution:
                break

        return ContactsForDepartment(
            department=department, tci=tci, tcs=tcs, solution=solution
        )


# ---------------------------------------------------------------------------
# Factory used by the FastAPI app
# ---------------------------------------------------------------------------


def make_repository_from_env() -> ContactsRepository:
    token = (os.environ.get("BASEROW_TOKEN") or "").strip()
    url = (os.environ.get("BASEROW_URL") or "").strip()
    if not token or not url:
        return MockContactsRepository()
    config = BaserowConfig(base_url=url, token=token)
    return BaserowContactsRepository(
        client=BaserowClient(config),
        tables=BaserowTables(
            clients=int(os.environ.get("BASEROW_TABLE_CLIENTS", "0") or "0"),
            contacts_force_vente=int(
                os.environ.get("BASEROW_TABLE_CONTACTS_FORCE_VENTE", "0") or "0"
            ),
            contacts_solution=int(
                os.environ.get("BASEROW_TABLE_CONTACTS_SOLUTION", "0") or "0"
            ),
        ),
    )
