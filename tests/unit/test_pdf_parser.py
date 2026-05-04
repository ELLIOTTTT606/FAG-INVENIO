"""Tests for the PDF parser."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from src.parser.pdf_parser import parse_pdf
from tests.fixtures.galletti_pdf import write_geg, write_pac


@pytest.fixture()
def schema_validator() -> Draft202012Validator:
    schema = json.loads(Path("src/schema/pac_geg_schema.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def test_parse_pac_pdf_extracts_cooling_and_heating(
    tmp_path: Path, schema_validator: Draft202012Validator
) -> None:
    fixture = write_pac(tmp_path / "pac.pdf")
    result = parse_pdf(fixture)
    data = result.data

    assert data["family"] == "PAC"
    assert data["model"] == "PLP"
    assert data["size"] == "052"
    assert data["type"] == "HS"

    cooling = data["conditions"]["cooling"]
    assert cooling["water_in_C"] == 12.0
    assert cooling["air_temp_C"] == 35.0

    heating = data["conditions"]["heating"]
    assert heating["water_in_C"] == 40.0
    assert heating["air_humidity_percent"] == 87

    perf_c = data["performance"]["cooling"]
    assert perf_c["power_kW"] == 41.7
    assert perf_c["eer"] == 2.5
    assert perf_c["seer"] == 4.15

    perf_h = data["performance"]["heating"]
    assert perf_h["power_kW"] == 52.3
    assert perf_h["cop"] == 3.37
    assert perf_h["seasonal_class"] == "A++"

    assert data["acoustic"]["free_field_distance_m"] == 10.0
    assert data["norm"]["uni_en_14511_applied"] is True
    assert data["general"]["refrigerant"] == "R290"

    assert not [w for w in result.warnings if w["code"] == "family_mismatch"]
    schema_validator.validate(data)


def test_parse_geg_pdf_has_no_heating_block(
    tmp_path: Path, schema_validator: Draft202012Validator
) -> None:
    fixture = write_geg(tmp_path / "geg.pdf")
    result = parse_pdf(fixture)
    data = result.data

    assert data["family"] == "GEG"
    assert data["type"] == "CS"

    assert data["performance"]["cooling"]["power_kW"] == 210.0
    heating = data["performance"].get("heating", {})
    assert heating == {} or all(v is None for v in heating.values())

    assert data["general"]["refrigerant"] == "R454B"
    assert data["general"]["sound_power_lw_dBA"] == 88.0

    assert not [w for w in result.warnings if w["code"] == "family_mismatch"]
    schema_validator.validate(data)


def test_parse_pdf_warns_when_no_text(tmp_path: Path) -> None:
    """An empty PDF (no text drawn) should raise pdf_no_text."""

    from reportlab.pdfgen import canvas  # local import to keep module import cheap

    path = tmp_path / "blank.pdf"
    canvas.Canvas(str(path)).save()

    result = parse_pdf(path)
    assert any(w["code"] == "pdf_no_text" for w in result.warnings)
