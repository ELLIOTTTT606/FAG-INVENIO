"""Tests for the DOCX parser."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from docx import Document
from jsonschema import Draft202012Validator

from src.parser.docx_parser import (
    DESIGNATION_RE,
    detect_designation,
    normalize_label,
    parse_docx,
)
from tests.fixtures.galletti_docx import write_geg, write_pac


def test_designation_regex_extracts_groups() -> None:
    line = "PLP052HS2B A000CE000I00110 0000000I000000000000"
    match = DESIGNATION_RE.search(line)
    assert match is not None
    assert match.group("model") == "PLP"
    assert match.group("size") == "052"
    assert match.group("heatcool") == "H"
    assert match.group("acoustic") == "S"


def test_detect_designation_returns_first_match() -> None:
    paragraphs = [
        "Fiche technique GALLETTI",
        "Reference : PLP052HS2B A000CE000I00110 0000000I000000000000",
    ]
    code, parts = detect_designation(paragraphs)
    assert code is not None
    assert parts is not None
    assert parts["model"] == "PLP"


def test_detect_designation_returns_none_when_absent() -> None:
    code, parts = detect_designation(["pas de code ici"])
    assert code is None
    assert parts is None


def test_normalize_label_strips_accents_and_punctuation() -> None:
    assert normalize_label("Puissance frigorifique :") == "puissance frigorifique"
    assert normalize_label("Temperature  exterieure (°C)") == "temperature exterieure c"


@pytest.fixture()
def schema_validator() -> Draft202012Validator:
    schema = json.loads(Path("src/schema/pac_geg_schema.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def test_parse_pac_fixture_extracts_cooling_and_heating(
    tmp_path: Path, schema_validator: Draft202012Validator
) -> None:
    fixture = write_pac(tmp_path / "pac.docx")
    result = parse_docx(fixture)
    data = result.data

    assert data["family"] == "PAC"
    assert data["model"] == "PLP"
    assert data["size"] == "052"
    assert data["type"] == "HS"

    cooling = data["conditions"]["cooling"]
    assert cooling["water_in_C"] == 12.0
    assert cooling["water_out_C"] == 7.0
    assert cooling["air_temp_C"] == 35.0
    assert cooling["load_percent"] == 100

    heating = data["conditions"]["heating"]
    assert heating["water_in_C"] == 40.0
    assert heating["water_out_C"] == 45.0
    assert heating["air_temp_C"] == 7.0
    assert heating["air_humidity_percent"] == 87

    perf_c = data["performance"]["cooling"]
    assert perf_c["power_kW"] == 41.7
    assert perf_c["water_flow_lph"] == 7155
    assert perf_c["eer"] == 2.5
    assert perf_c["seer"] == 4.15

    perf_h = data["performance"]["heating"]
    assert perf_h["power_kW"] == 52.3
    assert perf_h["cop"] == 3.37
    assert perf_h["scop"] == 4.35
    assert perf_h["seasonal_class"] == "A++"

    assert data["acoustic"]["free_field_distance_m"] == 10.0
    assert data["norm"]["uni_en_14511_applied"] is True

    general = data["general"]
    assert general["max_current_A"] == 56.0
    assert general["sound_power_lw_dBA"] == 83.0
    assert general["refrigerant"] == "R290"
    assert general["weight_kg"] == 500.0

    assert data["designation_blocks"]["block1"] == "A000CE000I00110"
    assert data["designation_blocks"]["block2"] == "0000000I000000000000"
    options_by_pos = {(o["block"], o["position"]): o for o in data["options"]}
    assert options_by_pos[(1, 0)]["character"] == "A"
    assert all(o["selected"] is True for o in data["options"])
    assert all(o["decoded"] is False for o in data["options"])  # template decoder is empty

    assert not [w for w in result.warnings if w["code"] == "family_mismatch"]
    schema_validator.validate(data)


def test_parse_geg_fixture_has_no_heating_block(
    tmp_path: Path, schema_validator: Draft202012Validator
) -> None:
    fixture = write_geg(tmp_path / "geg.docx")
    result = parse_docx(fixture)
    data = result.data

    assert data["family"] == "GEG"
    assert data["type"] == "CS"

    assert data["performance"]["cooling"]["power_kW"] == 210.0
    assert data["performance"].get("heating", {}) == {} or all(
        v is None for v in data["performance"].get("heating", {}).values()
    )
    assert "heating" not in data["conditions"] or data["conditions"]["heating"] == {}

    assert data["general"]["refrigerant"] == "R454B"
    assert data["general"]["sound_power_lw_dBA"] == 88.0

    # GEG fixture has designation "VLS202CS0A B000CE000I00220 0000000I0..." -> non-zero options
    assert data["designation_blocks"]["block1"].startswith("B")
    assert data["options"]
    assert all(o["block"] in (1, 2) for o in data["options"])

    assert not [w for w in result.warnings if w["code"] == "family_mismatch"]
    schema_validator.validate(data)


def test_parse_docx_warns_when_no_designation(tmp_path: Path) -> None:
    document = Document()
    document.add_paragraph("Aucun code de designation ici.")
    path = tmp_path / "no_design.docx"
    document.save(str(path))

    result = parse_docx(path)
    assert any(w["code"] == "designation_not_found" for w in result.warnings)
