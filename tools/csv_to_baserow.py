"""Push the options/accessoires CSV master file into Baserow.

Reads a CSV (typically the output of `tools.validate_csv`), groups rows
by an unique key, and either CREATEs them in Baserow or PATCHes the
matching existing rows when --upsert is set. Skips rows that already
exist by default so re-running the script is idempotent.

CLI:
    python -m tools.csv_to_baserow \\
        --input options_accessoires_master.csv \\
        --table-id 941070 \\
        --unique-key model,size,option_code \\
        [--field-map model=Modele option_code=Code ...] \\
        [--upsert] [--dry-run] [--batch-size 50]

Authentication: BASEROW_URL + BASEROW_TOKEN (env or --baserow-* flags).
Exit codes: 0 if every row was processed cleanly, 1 otherwise.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from itertools import islice
from pathlib import Path
from typing import Any

from src.services.baserow_client import BaserowClient, BaserowConfig, BaserowError


@dataclass
class SyncReport:
    total: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "created": self.created,
            "updated": self.updated,
            "skipped": self.skipped,
            "errors": self.errors,
            "ok": self.ok,
        }


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return []
        return [dict(row) for row in reader]


def _parse_field_map(items: Iterable[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"--field-map entries must be key=value, got {item!r}")
        key, value = item.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or not value:
            raise SystemExit(f"--field-map entry {item!r} must have non-empty parts")
        mapping[key] = value
    return mapping


def _project_row(
    row: dict[str, str], field_map: dict[str, str]
) -> dict[str, Any]:
    """Apply the field mapping (CSV column -> Baserow field name)."""

    if not field_map:
        return {k: v for k, v in row.items() if v != ""}
    out: dict[str, Any] = {}
    for csv_col, value in row.items():
        if value == "":
            continue
        target = field_map.get(csv_col, csv_col)
        out[target] = value
    return out


def _row_key(row: dict[str, str], unique_keys: tuple[str, ...]) -> tuple[str, ...]:
    return tuple((row.get(k) or "").strip().upper() for k in unique_keys)


def _existing_row_key(
    row: dict[str, Any], unique_keys: tuple[str, ...], field_map: dict[str, str]
) -> tuple[str, ...]:
    """Same key extraction but applied to a row coming back from Baserow."""

    parts: list[str] = []
    for canonical in unique_keys:
        baserow_field = field_map.get(canonical, canonical)
        value = row.get(baserow_field)
        if value is None:
            value = row.get(canonical)
        parts.append(str(value or "").strip().upper())
    return tuple(parts)


def _chunked(items: list[dict[str, Any]], size: int) -> Iterator[list[dict[str, Any]]]:
    if size <= 0:
        yield items
        return
    iterator = iter(items)
    while True:
        chunk = list(islice(iterator, size))
        if not chunk:
            return
        yield chunk


def sync_csv(
    *,
    client: BaserowClient,
    table_id: int,
    rows: list[dict[str, str]],
    unique_keys: tuple[str, ...],
    field_map: dict[str, str],
    upsert: bool = False,
    dry_run: bool = False,
    batch_size: int = 50,
) -> SyncReport:
    """Push `rows` into Baserow table `table_id`. Idempotent on `unique_keys`."""

    report = SyncReport(total=len(rows))
    if not rows:
        return report

    # Build an index of existing rows by key. id key may live under "id".
    existing_by_key: dict[tuple[str, ...], int] = {}
    for existing in client.iter_all_rows(table_id):
        key = _existing_row_key(existing, unique_keys, field_map)
        if not any(key):
            continue
        row_id = existing.get("id")
        if isinstance(row_id, int):
            existing_by_key[key] = row_id

    to_create: list[dict[str, Any]] = []
    to_update: list[tuple[int, dict[str, Any]]] = []

    for csv_row in rows:
        key = _row_key(csv_row, unique_keys)
        if not any(key):
            report.errors.append(f"row missing unique key {unique_keys}: {csv_row!r}")
            continue
        payload = _project_row(csv_row, field_map)
        if key in existing_by_key:
            if upsert:
                to_update.append((existing_by_key[key], payload))
            else:
                report.skipped += 1
        else:
            to_create.append(payload)

    if dry_run:
        report.created = len(to_create)
        report.updated = len(to_update)
        return report

    for chunk in _chunked(to_create, batch_size):
        try:
            created = client.create_rows(table_id, chunk)
            report.created += len(created) or len(chunk)
        except BaserowError as err:
            report.errors.append(f"batch create failed ({len(chunk)} rows): {err}")

    for row_id, payload in to_update:
        try:
            client.update_row(table_id, row_id, payload)
            report.updated += 1
        except BaserowError as err:
            report.errors.append(f"update of row {row_id} failed: {err}")

    return report


# ---------------------------------------------------------------------------
# CLI plumbing
# ---------------------------------------------------------------------------


def _make_client(url: str, token: str) -> BaserowClient:
    if not url:
        raise SystemExit("Baserow URL not provided. Set BASEROW_URL or use --baserow-url.")
    if not token:
        raise SystemExit("Baserow token not provided. Set BASEROW_TOKEN or use --baserow-token.")
    return BaserowClient(BaserowConfig(base_url=url, token=token))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="csv-to-baserow",
        description="Push (or upsert) a CSV into a Baserow table, idempotently.",
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--table-id", required=True, type=int)
    parser.add_argument(
        "--unique-key",
        default="model,size,option_code",
        help="Comma-separated CSV columns forming the deduplication key.",
    )
    parser.add_argument(
        "--field-map",
        nargs="*",
        default=[],
        help="Override Baserow field names per CSV column, e.g. model=Modele.",
    )
    parser.add_argument("--upsert", action="store_true", help="PATCH existing rows.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--baserow-url", default=os.environ.get("BASEROW_URL", ""))
    parser.add_argument("--baserow-token", default=os.environ.get("BASEROW_TOKEN", ""))
    parser.add_argument("--json", action="store_true", help="Emit a machine-readable report.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    field_map = _parse_field_map(args.field_map)
    unique_keys = tuple(k.strip() for k in args.unique_key.split(",") if k.strip())
    if not unique_keys:
        print("--unique-key cannot be empty.", file=sys.stderr)
        return 2

    rows = _read_csv(args.input)

    if args.dry_run and (not args.baserow_url or not args.baserow_token):
        # Allow dry-run without credentials: skip the existing-row scan.
        report = SyncReport(total=len(rows))
        existing: dict[tuple[str, ...], int] = {}
        for csv_row in rows:
            key = _row_key(csv_row, unique_keys)
            if not any(key):
                report.errors.append(
                    f"row missing unique key {unique_keys}: {csv_row!r}"
                )
                continue
            if key in existing:
                report.skipped += 1
            else:
                report.created += 1
                existing[key] = 0
    else:
        with _make_client(args.baserow_url, args.baserow_token) as client:
            report = sync_csv(
                client=client,
                table_id=args.table_id,
                rows=rows,
                unique_keys=unique_keys,
                field_map=field_map,
                upsert=args.upsert,
                dry_run=args.dry_run,
                batch_size=args.batch_size,
            )

    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(
            f"rows={report.total} created={report.created} "
            f"updated={report.updated} skipped={report.skipped} "
            f"errors={len(report.errors)} dry_run={args.dry_run}"
        )
        for err in report.errors[:10]:
            print(f"  ERR {err}", file=sys.stderr)

    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
