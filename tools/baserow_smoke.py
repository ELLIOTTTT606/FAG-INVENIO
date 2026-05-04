"""End-to-end Baserow diagnostic.

Run this once a Baserow instance is configured to verify that the token,
URL, and table IDs all line up with the FA dataset. Probes:

  - the tokens/check endpoint (auth);
  - one page of every configured table (count + a sample row);
  - the high-level use cases (search clients, get contacts for one
    department, list options for one (model, type, size)).

The script does not perform writes; it is safe to run against production.

Usage:
    BASEROW_URL=https://api.baserow.io BASEROW_TOKEN=*** \
    BASEROW_TABLE_CLIENTS=939119 \
    BASEROW_TABLE_CONTACTS_FORCE_VENTE=939355 \
    BASEROW_TABLE_CONTACTS_SOLUTION=939361 \
    BASEROW_TABLE_OPTIONS_ACCESSOIRES=941070 \
    python -m tools.baserow_smoke

Exit codes: 0 on success, 1 if any probe fails.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any

from src.services.baserow_client import BaserowClient, BaserowConfig, BaserowError
from src.services.contacts_repo import (
    BaserowContactsRepository,
    BaserowTables,
)
from src.services.options_catalog import BaserowOptionsCatalog
from src.services.settings import Settings, get_settings


@dataclass
class ProbeResult:
    name: str
    ok: bool
    message: str
    details: dict[str, Any]


def _probe_table(
    client: BaserowClient, name: str, table_id: int, sample_keys: tuple[str, ...] = ()
) -> ProbeResult:
    if not table_id:
        return ProbeResult(name=name, ok=False, message="not configured", details={"table_id": 0})
    try:
        page = client.list_rows(table_id, page=1, size=5)
    except BaserowError as err:
        return ProbeResult(name=name, ok=False, message=str(err), details={"table_id": table_id})
    rows = page.get("results") or []
    sample: dict[str, Any] = {}
    if rows and sample_keys:
        first = rows[0]
        sample = {key: first.get(key) for key in sample_keys}
    return ProbeResult(
        name=name,
        ok=True,
        message=f"{page.get('count', len(rows))} row(s)",
        details={
            "table_id": table_id,
            "count": page.get("count"),
            "sample_keys": list(sample.keys()) if sample else [],
            "sample": sample,
        },
    )


def _probe_clients(
    client: BaserowClient, tables: BaserowTables, query: str
) -> ProbeResult:
    repo = BaserowContactsRepository(client=client, tables=tables)
    try:
        matches = repo.search_clients(query, limit=3)
    except BaserowError as err:
        return ProbeResult(
            name="search_clients", ok=False, message=str(err), details={"query": query}
        )
    return ProbeResult(
        name="search_clients",
        ok=True,
        message=f"{len(matches)} match(es) for {query!r}",
        details={"query": query, "first": matches[0].to_dict() if matches else None},
    )


def _probe_contacts(
    client: BaserowClient, tables: BaserowTables, department: str
) -> ProbeResult:
    repo = BaserowContactsRepository(client=client, tables=tables)
    try:
        result = repo.get_contacts_for_department(department)
    except BaserowError as err:
        return ProbeResult(
            name="contacts_for_department",
            ok=False,
            message=str(err),
            details={"department": department},
        )
    return ProbeResult(
        name="contacts_for_department",
        ok=True,
        message=f"resolved department {department}",
        details={
            "department": department,
            "tci": bool(result.tci),
            "tcs": bool(result.tcs),
            "solution": bool(result.solution),
        },
    )


def _probe_options(
    client: BaserowClient, table_id: int, model: str, type_: str, size: str
) -> ProbeResult:
    if not table_id:
        return ProbeResult(
            name="list_options", ok=False, message="options table not configured", details={}
        )
    catalog = BaserowOptionsCatalog(client=client, table_id=table_id)
    try:
        options = catalog.list_options(model=model, type_=type_, size=size)
    except BaserowError as err:
        return ProbeResult(
            name="list_options", ok=False, message=str(err), details={"model": model}
        )
    return ProbeResult(
        name="list_options",
        ok=True,
        message=f"{len(options)} option(s) for {model}/{type_}/{size}",
        details={"sample_codes": [opt.code for opt in options[:5]]},
    )


def run_probes(settings: Settings, *, sample_query: str, sample_department: str,
                sample_model: str, sample_type: str, sample_size: str) -> list[ProbeResult]:
    if not settings.baserow_live:
        return [
            ProbeResult(
                name="config",
                ok=False,
                message="BASEROW_URL/BASEROW_TOKEN missing; cannot probe",
                details={
                    "baserow_url": bool(settings.baserow_url),
                    "baserow_token": bool(settings.baserow_token),
                },
            )
        ]

    config = BaserowConfig(
        base_url=settings.baserow_url,
        token=settings.baserow_token,
        timeout_seconds=settings.baserow_timeout_seconds,
        max_retries=settings.baserow_max_retries,
        cache_ttl_seconds=0,  # disable cache during diagnostics
    )
    tables = BaserowTables(
        clients=settings.baserow_table_clients,
        contacts_force_vente=settings.baserow_table_contacts_force_vente,
        contacts_solution=settings.baserow_table_contacts_solution,
    )

    with BaserowClient(config) as client:
        results: list[ProbeResult] = []
        results.append(
            ProbeResult(
                name="auth",
                ok=client.ping(),
                message="ok" if client.ping() else "auth check failed",
                details={"url": settings.baserow_url},
            )
        )
        results.append(
            _probe_table(
                client,
                "table.CLIENTS",
                tables.clients,
                ("client_name", "client_code", "department"),
            )
        )
        results.append(
            _probe_table(
                client,
                "table.contacts_force_vente",
                tables.contacts_force_vente,
                ("departments", "tci_name", "tcs_name"),
            )
        )
        results.append(
            _probe_table(
                client,
                "table.contacts_solution",
                tables.contacts_solution,
                ("name", "email", "phone"),
            )
        )
        results.append(
            _probe_table(
                client,
                "table.options_accessoires",
                settings.baserow_table_options_accessoires,
                ("model", "type", "size", "option_code", "label_fr"),
            )
        )
        results.append(_probe_clients(client, tables, sample_query))
        results.append(_probe_contacts(client, tables, sample_department))
        results.append(
            _probe_options(
                client,
                settings.baserow_table_options_accessoires,
                sample_model,
                sample_type,
                sample_size,
            )
        )

    return results


def _print_human(results: list[ProbeResult]) -> None:
    width = max(len(r.name) for r in results) + 2
    for result in results:
        icon = "✓" if result.ok else "✗"
        print(f"  {icon} {result.name.ljust(width)} {result.message}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="baserow-smoke", description=__doc__)
    parser.add_argument("--sample-query", default="lyon")
    parser.add_argument("--sample-department", default="69")
    parser.add_argument("--sample-model", default="PLP")
    parser.add_argument("--sample-type", default="HS")
    parser.add_argument("--sample-size", default="052")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args(argv)

    settings = get_settings()
    results = run_probes(
        settings,
        sample_query=args.sample_query,
        sample_department=args.sample_department,
        sample_model=args.sample_model,
        sample_type=args.sample_type,
        sample_size=args.sample_size,
    )

    if args.json:
        print(
            json.dumps(
                [
                    {
                        "name": r.name,
                        "ok": r.ok,
                        "message": r.message,
                        "details": r.details,
                    }
                    for r in results
                ],
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(f"baserow mode: {settings.baserow_mode}")
        print(f"baserow url:  {settings.baserow_url or '(not set)'}")
        print()
        _print_human(results)

    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
