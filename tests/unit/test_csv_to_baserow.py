"""Tests for tools.csv_to_baserow."""

from __future__ import annotations

import csv as csv_lib
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

from src.services.baserow_client import BaserowClient, BaserowConfig
from tools import csv_to_baserow


def _baserow(handler: httpx.MockTransport) -> BaserowClient:
    config = BaserowConfig(base_url="https://baserow.test", token="dummy")
    return BaserowClient(
        config,
        client=httpx.Client(
            base_url=config.base_url, headers=config.headers, transport=handler
        ),
        sleep=lambda _: None,
    )


def _row(model: str = "PLP", size: str = "052", code: str = "P", **extra: str) -> dict[str, str]:
    base = {
        "model": model,
        "size": size,
        "option_code": code,
        "label_fr": f"label-{code}",
    }
    base.update(extra)
    return base


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        path.write_text("model,size,option_code,label_fr\n", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv_lib.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _route(routes: dict[str, Callable[[httpx.Request], httpx.Response]]) -> httpx.MockTransport:
    def handle(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        for prefix, fn in routes.items():
            if prefix in url:
                return fn(request)
        return httpx.Response(404, text=f"unhandled: {request.method} {url}")

    return httpx.MockTransport(handle)


def test_parse_field_map_rejects_invalid_format() -> None:
    with pytest.raises(SystemExit):
        csv_to_baserow._parse_field_map(["no_equals"])
    with pytest.raises(SystemExit):
        csv_to_baserow._parse_field_map(["=value"])


def test_project_row_uses_identity_mapping_when_field_map_empty() -> None:
    out = csv_to_baserow._project_row({"a": "1", "b": "", "c": "x"}, {})
    assert out == {"a": "1", "c": "x"}


def test_project_row_remaps_columns_per_field_map() -> None:
    out = csv_to_baserow._project_row(
        {"model": "PLP", "size": "052"}, {"model": "Modele"}
    )
    assert out == {"Modele": "PLP", "size": "052"}


def test_sync_creates_only_missing_rows(tmp_path: Path) -> None:
    posted: list[list[dict[str, object]]] = []
    existing = [
        {"id": 1, "model": "PLP", "size": "052", "option_code": "P", "label_fr": "exists"}
    ]

    def list_rows(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": existing, "next": None})

    def batch(request: httpx.Request) -> httpx.Response:
        body = request.read()
        items = []
        # parse JSON body
        import json as _json

        items = _json.loads(body).get("items", [])
        posted.append(items)
        return httpx.Response(
            200, json={"items": [{"id": 99 + i, **item} for i, item in enumerate(items)]}
        )

    transport = _route(
        {"/batch/": batch, "/table/7/": list_rows}
    )
    rows = [_row(code="P"), _row(code="Q"), _row(code="R")]
    csv_path = tmp_path / "in.csv"
    _write_csv(csv_path, rows)

    with _baserow(transport) as client:
        report = csv_to_baserow.sync_csv(
            client=client,
            table_id=7,
            rows=csv_to_baserow._read_csv(csv_path),
            unique_keys=("model", "size", "option_code"),
            field_map={},
            upsert=False,
            dry_run=False,
            batch_size=10,
        )

    assert report.created == 2
    assert report.skipped == 1  # the existing P row
    assert report.errors == []
    assert posted and {row["option_code"] for row in posted[0]} == {"Q", "R"}


def test_sync_upsert_patches_existing_rows(tmp_path: Path) -> None:
    patched: list[tuple[int, dict[str, object]]] = []
    existing = [
        {"id": 42, "model": "PLP", "size": "052", "option_code": "P", "label_fr": "old"}
    ]

    def list_rows(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": existing, "next": None})

    def patch(request: httpx.Request) -> httpx.Response:
        # path looks like /api/database/rows/table/7/42/ (ignore query string)
        row_id = int(request.url.path.rstrip("/").split("/")[-1])
        import json as _json

        patched.append((row_id, _json.loads(request.read())))
        return httpx.Response(200, json={"id": row_id})

    transport = _route(
        {
            "/batch/": lambda r: httpx.Response(
                500, text="batch should not be called when only updates"
            ),
            "/table/7/42/": patch,
            "/table/7/": list_rows,
        }
    )
    rows = [_row(code="P", label_fr="new")]
    csv_path = tmp_path / "in.csv"
    _write_csv(csv_path, rows)

    with _baserow(transport) as client:
        report = csv_to_baserow.sync_csv(
            client=client,
            table_id=7,
            rows=csv_to_baserow._read_csv(csv_path),
            unique_keys=("model", "size", "option_code"),
            field_map={},
            upsert=True,
        )

    assert report.created == 0
    assert report.updated == 1
    assert patched == [(42, {"model": "PLP", "size": "052", "option_code": "P", "label_fr": "new"})]


def test_sync_dry_run_does_not_call_baserow_for_writes(tmp_path: Path) -> None:
    existing = [
        {"id": 1, "model": "PLP", "size": "052", "option_code": "P", "label_fr": "x"}
    ]

    def list_rows(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": existing, "next": None})

    def write(_: httpx.Request) -> httpx.Response:
        raise AssertionError("dry run should not POST or PATCH")

    transport = _route({"/batch/": write, "/table/7/1/": write, "/table/7/": list_rows})
    rows = [_row(code="P"), _row(code="Q")]
    csv_path = tmp_path / "in.csv"
    _write_csv(csv_path, rows)

    with _baserow(transport) as client:
        report = csv_to_baserow.sync_csv(
            client=client,
            table_id=7,
            rows=csv_to_baserow._read_csv(csv_path),
            unique_keys=("model", "size", "option_code"),
            field_map={},
            dry_run=True,
        )

    assert report.created == 1  # the new Q row
    assert report.skipped == 1  # the existing P row
    assert report.updated == 0
    assert report.errors == []


def test_sync_records_error_on_failed_create(tmp_path: Path) -> None:
    def list_rows(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": [], "next": None})

    def fail(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    transport = _route({"/batch/": fail, "/table/7/": list_rows})
    rows = [_row(code="Q")]
    csv_path = tmp_path / "in.csv"
    _write_csv(csv_path, rows)

    with _baserow(transport) as client:
        report = csv_to_baserow.sync_csv(
            client=client,
            table_id=7,
            rows=csv_to_baserow._read_csv(csv_path),
            unique_keys=("model", "size", "option_code"),
            field_map={},
            batch_size=10,
        )

    assert report.created == 0
    assert report.errors and "batch create failed" in report.errors[0]


def test_sync_flags_row_missing_unique_key() -> None:
    rows: list[dict[str, str]] = [{"model": "", "size": "", "option_code": "", "label_fr": "no key"}]

    def list_rows(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": [], "next": None})

    transport = _route({"/table/7/": list_rows})

    with _baserow(transport) as client:
        report = csv_to_baserow.sync_csv(
            client=client,
            table_id=7,
            rows=rows,
            unique_keys=("model", "size", "option_code"),
            field_map={},
        )

    assert report.created == 0
    assert report.errors and "missing unique key" in report.errors[0]


def test_chunked_splits_payload() -> None:
    items = [{"i": i} for i in range(7)]
    chunks = list(csv_to_baserow._chunked(items, 3))
    assert [len(c) for c in chunks] == [3, 3, 1]
