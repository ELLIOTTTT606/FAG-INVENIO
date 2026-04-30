"""Tests for the HTML + PDF generator."""

from __future__ import annotations

import builtins

import pytest

from src.services.pdf_generator import (
    GenerationContext,
    PdfEngineUnavailableError,
    render_html,
    render_pdf,
    suggested_filename,
)


def _record() -> dict[str, object]:
    return {
        "family": "PAC",
        "model": "PLP",
        "size": "052",
        "type": "HS",
        "designation_code": "PLP052HS2B A000CE000I00110 0000000I000000000000",
        "designation_blocks": {"block1": "A000CE000I00110", "block2": "0000000I000000000000"},
        "conditions": {
            "cooling": {"water_in_C": 12.0, "water_out_C": 7.0, "air_temp_C": 35.0, "load_percent": 100},
            "heating": {"water_in_C": 40.0, "water_out_C": 45.0, "air_temp_C": 7.0, "load_percent": 100},
        },
        "performance": {
            "cooling": {"power_kW": 41.7, "water_flow_lph": 7155, "eer": 2.5, "seer": 4.15},
            "heating": {"power_kW": 52.3, "cop": 3.37, "scop": 4.35, "seasonal_class": "A++"},
        },
        "general": {
            "max_current_A": 56.0,
            "sound_power_lw_dBA": 83.0,
            "refrigerant": "R290",
            "weight_kg": 500.0,
            "supply": "400 / 3+N / 50",
            "gwp": 3.0,
        },
        "options": [
            {
                "code": "P",
                "category": "Kit antigel",
                "label": "Protection echangeur",
                "description": "Resistance + traceur thermique",
                "tips": "Climat froid",
                "price_eur": 199.0,
                "selected": True,
                "block": 1,
                "position": 4,
                "character": "C",
                "decoded": True,
            },
            {
                "code": "B1P00",
                "category": "designation",
                "label": "Option codee position B1P00 = 'A' (a renseigner)",
                "description": None,
                "tips": None,
                "price_eur": None,
                "selected": True,
                "block": 1,
                "position": 0,
                "character": "A",
                "decoded": False,
            },
        ],
        "warnings": [],
        "acoustic": {},
        "norm": {},
        "hydraulics": {},
    }


def _contacts() -> dict[str, object]:
    return {
        "department": "69",
        "tci": {"name": "Camille Durand", "email": "c.durand@x.com", "phone": "04 72 00 12 34"},
        "tcs": {"name": "Paul Lefevre", "email": "p.lefevre@x.com", "phone": "04 72 00 12 35"},
        "solution": {
            "name": "Solutions Habitat",
            "email": "solutions.habitat@x.com",
            "phone": "04 48 40 40 40",
        },
    }


def test_render_html_includes_machine_identity_and_toc() -> None:
    html = render_html(GenerationContext(record=_record(), contacts=_contacts(),
                                         selected_option_codes=("P",)))
    assert "PLP" in html and "052" in html and "HS" in html
    assert "id=\"toc\"" in html
    assert "Sommaire" in html
    assert "Données techniques de sélection" in html
    # Selected option appears, others are filtered out
    assert "Protection echangeur" in html
    # Cooling perf is rendered
    assert "41.7" in html
    # Designation full string surfaces on the cover
    assert "A000CE000I00110" in html


def test_render_html_renders_no_heating_message_for_geg() -> None:
    record = _record()
    record["family"] = "GEG"
    record["type"] = "CS"
    record["performance"]["heating"] = {}
    html = render_html(GenerationContext(record=record))
    assert "Mode chauffage non applicable" in html


def test_render_html_displays_warning_banner() -> None:
    record = _record()
    record["warnings"] = [
        {"code": "designation_decoder_missing", "field": "options", "message": "Set me up"}
    ]
    html = render_html(GenerationContext(record=record))
    assert "designation_decoder_missing" in html
    assert "1 avertissement" in html


def test_render_html_falls_back_to_record_selected_options_when_codes_empty() -> None:
    record = _record()
    record["options"][0]["selected"] = False  # P
    record["options"][1]["selected"] = True   # B1P00
    html = render_html(GenerationContext(record=record))
    assert "B1P00" in html
    assert "Protection echangeur" not in html


def test_render_html_marks_missing_values() -> None:
    record = _record()
    record["general"]["refrigerant"] = None
    html = render_html(GenerationContext(record=record))
    assert "Donnée non disponible" in html


def test_render_pdf_returns_pdf_bytes() -> None:
    pdf = render_pdf(GenerationContext(record=_record(), contacts=_contacts(),
                                       selected_option_codes=("P",)))
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 1000


def test_render_pdf_raises_when_weasyprint_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "weasyprint":
            raise ImportError("not installed in this test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(PdfEngineUnavailableError):
        render_pdf(GenerationContext(record=_record()))


def test_suggested_filename_slugifies_machine_identity() -> None:
    assert suggested_filename(_record()) == "INVENIO-plp-052-hs.pdf"
    assert suggested_filename({}, "html") == "INVENIO-fiche.html"
