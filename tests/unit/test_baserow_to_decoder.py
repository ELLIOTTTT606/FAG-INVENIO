"""Tests for tools.baserow_to_decoder."""

from __future__ import annotations

import csv
from collections.abc import Iterable
from pathlib import Path

import httpx
import pytest

from src.parser.designation import load_decoder
from src.services.baserow_client import BaserowClient, BaserowConfig
from tools.baserow_to_decoder import (
    DECODER_COLUMNS,
    _parse_field_map,
    _project_row,
    export_decoder,
)


def _client(handler: httpx.MockTransport) -> BaserowClient:
    config = BaserowConfig(base_url="https://baserow.test", token="dummy")
    return BaserowClient(
        config,
        client=httpx.Client(
            base_url=config.base_url,
            headers=config.headers,
            transport=handler,
        ),
    )


def _paged_handler(pages: list[list[dict[str, object]]]) -> httpx.MockTransport:
    """Return a transport that serves successive pages of `results`."""

    def handle(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params.get("page", "1"))
        if page < 1 or page > len(pages):
            return httpx.Response(200, json={"results": [], "next": None})
        results = pages[page - 1]
        is_last = page == len(pages)
        return httpx.Response(
            200,
            json={
                "results": results,
                "next": None if is_last else f"https://baserow.test/page/{page + 1}",
            },
        )

    return httpx.MockTransport(handle)


def _row(**fields: object) -> dict[str, object]:
    base = {
        "family": "PAC",
        "block": 1,
        "position": 0,
        "character": "A",
        "code": "A",
        "category": "Compresseur",
        "label_fr": "Scroll modulant",
        "description_fr": "Compresseur scroll modulant inverter",
        "tips_fr": "",
    }
    base.update(fields)
    return base


def test_parse_field_map_defaults_to_identity() -> None:
    result = _parse_field_map([])
    assert result == {c: c for c in DECODER_COLUMNS}


def test_parse_field_map_overrides_only_listed_columns() -> None:
    result = _parse_field_map(["family=Famille", "label_fr=Libelle"])
    assert result["family"] == "Famille"
    assert result["label_fr"] == "Libelle"
    assert result["block"] == "block"


def test_parse_field_map_rejects_unknown_columns() -> None:
    with pytest.raises(SystemExit):
        _parse_field_map(["unknown=Foo"])


def test_parse_field_map_rejects_invalid_format() -> None:
    with pytest.raises(SystemExit):
        _parse_field_map(["no_equals_sign"])


def test_project_row_uses_field_map_for_remapped_keys() -> None:
    row = {"Famille": "PAC", "Bloc": 1, "Position": 0, "Caractere": "A", "Libelle": "Scroll"}
    field_map = {c: c for c in DECODER_COLUMNS}
    field_map["family"] = "Famille"
    field_map["block"] = "Bloc"
    field_map["position"] = "Position"
    field_map["character"] = "Caractere"
    field_map["label_fr"] = "Libelle"
    projected = _project_row(row, field_map)
    assert projected["family"] == "PAC"
    assert projected["block"] == "1"
    assert projected["label_fr"] == "Scroll"
    # missing columns become empty strings, not crashes
    assert projected["tips_fr"] == ""


def test_export_decoder_writes_valid_csv_and_loads_rules(tmp_path: Path) -> None:
    pages = [
        [_row(position=0, character="A"), _row(position=4, character="C", code="C")],
        [_row(family="GEG", position=7, character="I", code="I", category="Hydraulique")],
    ]
    output = tmp_path / "decoder.csv"

    with _client(_paged_handler(pages)) as client:
        rows_seen, rules_loaded = export_decoder(
            client=client,
            table_id=42,
            output=output,
            field_map={c: c for c in DECODER_COLUMNS},
        )

    assert rows_seen == 3
    assert rules_loaded == 3
    decoder = load_decoder(output)
    assert decoder.lookup("PAC", 1, 0, "A") is not None
    assert decoder.lookup("GEG", 1, 7, "I") is not None


def test_export_decoder_handles_empty_table(tmp_path: Path) -> None:
    output = tmp_path / "empty.csv"
    with _client(_paged_handler([[]])) as client:
        rows_seen, rules_loaded = export_decoder(
            client=client,
            table_id=42,
            output=output,
            field_map={c: c for c in DECODER_COLUMNS},
        )
    assert rows_seen == 0
    assert rules_loaded == 0
    # Empty CSV still has the canonical header
    with output.open(encoding="utf-8") as f:
        header = next(csv.reader(f))
    assert header == list(DECODER_COLUMNS)


def test_export_decoder_with_remapped_field_names(tmp_path: Path) -> None:
    rows: Iterable[dict[str, object]] = [
        {
            "Famille": "PAC",
            "Bloc": 1,
            "Position": 0,
            "Caractere": "A",
            "Code": "A",
            "Categorie": "Compresseur",
            "Libelle": "Scroll modulant",
            "Description": "",
            "Tips": "",
        }
    ]
    output = tmp_path / "remap.csv"
    field_map = {c: c for c in DECODER_COLUMNS}
    field_map.update(
        {
            "family": "Famille",
            "block": "Bloc",
            "position": "Position",
            "character": "Caractere",
            "code": "Code",
            "category": "Categorie",
            "label_fr": "Libelle",
            "description_fr": "Description",
            "tips_fr": "Tips",
        }
    )
    with _client(_paged_handler([list(rows)])) as client:
        _, rules_loaded = export_decoder(
            client=client, table_id=1, output=output, field_map=field_map
        )
    assert rules_loaded == 1
    rule = load_decoder(output).lookup("PAC", 1, 0, "A")
    assert rule is not None
    assert rule.label_fr == "Scroll modulant"
