"""Pull the GALLETTI designation decoder from Baserow into a local CSV.

This script reads every row of a Baserow table holding the position-based
decoding rules `(family, block, position, character) -> option metadata`
and writes them into the CSV consumed by `src.parser.designation`.

CLI:
    python -m tools.baserow_to_decoder \\
        --table-id 941070 \\
        --output src/parser/designation_decoder.csv \\
        [--baserow-url https://api.baserow.io] \\
        [--field-map family=Famille block=Bloc position=Position \\
                     character=Caractere code=Code category=Categorie \\
                     label_fr=Libelle description_fr=Description tips_fr=Tips]

Authentication: the Baserow database token must be in `BASEROW_TOKEN`
(or passed via `--baserow-token`). The URL defaults to the value of
`BASEROW_URL` (typically https://api.baserow.io).

Exit codes: 0 on success, 1 if the Baserow call fails or the resulting
CSV holds zero valid decoder rules (likely a field-mapping issue).
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from src.parser.designation import load_decoder
from src.services.baserow_client import BaserowClient, BaserowConfig, BaserowError

DECODER_COLUMNS: tuple[str, ...] = (
    "family",
    "block",
    "position",
    "character",
    "code",
    "category",
    "label_fr",
    "description_fr",
    "tips_fr",
)


def _parse_field_map(items: Iterable[str]) -> dict[str, str]:
    mapping: dict[str, str] = {c: c for c in DECODER_COLUMNS}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"--field-map entries must be key=value, got {item!r}")
        key, value = item.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key not in DECODER_COLUMNS:
            raise SystemExit(
                f"unknown decoder column {key!r}. "
                f"Allowed: {', '.join(DECODER_COLUMNS)}."
            )
        mapping[key] = value
    return mapping


def _project_row(row: dict[str, Any], field_map: dict[str, str]) -> dict[str, str]:
    projected: dict[str, str] = {}
    for canonical_key in DECODER_COLUMNS:
        source_key = field_map[canonical_key]
        value = row.get(source_key)
        projected[canonical_key] = "" if value is None else str(value).strip()
    return projected


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(DECODER_COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def export_decoder(
    *,
    client: BaserowClient,
    table_id: int,
    output: Path,
    field_map: dict[str, str],
) -> tuple[int, int]:
    """Iterate every row, project, write CSV. Return (rows_seen, rules_loaded)."""

    projected_rows: list[dict[str, str]] = []
    rows_seen = 0
    for row in client.iter_all_rows(table_id):
        rows_seen += 1
        projected_rows.append(_project_row(row, field_map))

    _write_csv(output, projected_rows)

    decoder = load_decoder(output)
    return rows_seen, len(decoder.rules)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="baserow-to-decoder",
        description="Sync the GALLETTI designation decoder CSV from Baserow.",
    )
    parser.add_argument("--table-id", required=True, type=int)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("src/parser/designation_decoder.csv"),
    )
    parser.add_argument("--baserow-url", default=os.environ.get("BASEROW_URL", ""))
    parser.add_argument("--baserow-token", default=os.environ.get("BASEROW_TOKEN", ""))
    parser.add_argument(
        "--field-map",
        nargs="*",
        default=[],
        help="Override Baserow field names per decoder column, e.g. family=Famille.",
    )
    return parser


def _make_client(url: str, token: str) -> BaserowClient:
    if not url:
        raise SystemExit(
            "Baserow URL not provided. Set BASEROW_URL or use --baserow-url."
        )
    if not token:
        raise SystemExit(
            "Baserow token not provided. Set BASEROW_TOKEN or use --baserow-token."
        )
    config = BaserowConfig(base_url=url, token=token)
    return BaserowClient(config)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    field_map = _parse_field_map(args.field_map)

    try:
        with _make_client(args.baserow_url, args.baserow_token) as client:
            rows_seen, rules_loaded = export_decoder(
                client=client,
                table_id=args.table_id,
                output=args.output,
                field_map=field_map,
            )
    except BaserowError as err:
        print(f"baserow error: {err}", file=sys.stderr)
        return 1

    print(
        f"baserow rows fetched: {rows_seen} "
        f"-> decoder rules loaded: {rules_loaded} "
        f"-> wrote {args.output}"
    )
    if rows_seen == 0:
        print(
            "warning: no rows returned; check the table id and your token permissions.",
            file=sys.stderr,
        )
    elif rules_loaded == 0:
        print(
            "error: 0 valid decoder rules loaded from the exported CSV. "
            "This usually means the field mapping is wrong "
            "(use --field-map family=... block=...).",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
