"""Tests for the DOCX parser MVP."""

from __future__ import annotations

from pathlib import Path

import pytest
from docx import Document

from src.parser.docx_parser import (
    DESIGNATION_RE,
    detect_designation,
    normalize_label,
    parse_docx,
)


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
        "Autres infos",
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
def sample_docx(tmp_path: Path) -> Path:
    """Build a minimal DOCX with a designation line and a small table."""

    document = Document()
    document.add_paragraph("Fiche technique - extraction MVP")
    document.add_paragraph("Reference: PLP052HS2B A000CE000I00110 0000000I000000000000")

    table = document.add_table(rows=4, cols=3)
    table.rows[0].cells[0].text = "Puissance frigorifique"
    table.rows[0].cells[1].text = "kW"
    table.rows[0].cells[2].text = "41,7"

    table.rows[1].cells[0].text = "Puissance calorifique"
    table.rows[1].cells[1].text = "kW"
    table.rows[1].cells[2].text = "52.3"

    table.rows[2].cells[0].text = "Courant maximum"
    table.rows[2].cells[1].text = "A"
    table.rows[2].cells[2].text = "56"

    table.rows[3].cells[0].text = "Debit eau"
    table.rows[3].cells[1].text = "l/h"
    table.rows[3].cells[2].text = "7200"

    out = tmp_path / "sample.docx"
    document.save(str(out))
    return out


def test_parse_docx_extracts_designation_and_metrics(sample_docx: Path) -> None:
    result = parse_docx(sample_docx)

    assert result.data["model"] == "PLP"
    assert result.data["size"] == "052"
    assert result.data["type"] == "HS"
    assert result.data["designation_code"] is not None

    perf = result.data["performance"]
    assert perf["cooling_power_kW"] == 41.7
    assert perf["heating_power_kW"] == 52.3

    assert result.data["electrical"]["max_current_A"] == 56.0
    assert result.data["hydraulics"]["water_flow_lph"] == 7200

    assert result.data["source"]["filename"] == "sample.docx"
    assert result.data["source"]["format"] == "docx"


def test_parse_docx_warns_when_no_designation(tmp_path: Path) -> None:
    document = Document()
    document.add_paragraph("Aucun code de designation ici.")
    path = tmp_path / "no_design.docx"
    document.save(str(path))

    result = parse_docx(path)
    assert any(w["code"] == "designation_not_found" for w in result.warnings)
