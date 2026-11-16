"""Tests for the HTML + PDF generator of the INVENIO fiche."""

from __future__ import annotations

import builtins
import copy
from datetime import UTC, datetime

import pytest

from src.services.options_catalog import MockOptionsCatalog
from src.services.pdf_generator import (
    GenerationContext,
    PdfEngineUnavailableError,
    PlanImage,
    render_html,
    render_pdf,
    suggested_filename,
)

_NOW = datetime(2026, 11, 16, 9, 0, tzinfo=UTC)


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
            "cooling": {
                "power_kW": 41.7,
                "water_flow_lph": 7155,
                "eer": 2.5,
                "seer": 4.15,
                "total_power_kW": 16.6,
            },
            "heating": {
                "power_kW": 52.3,
                "cop": 3.37,
                "scop": 4.35,
                "seasonal_class": "A++",
                "total_power_kW": 15.5,
            },
        },
        "general": {
            "max_current_A": 56.0,
            "sound_power_lw_dBA": 83.0,
            "sound_pressure_lp_dBA": 55.0,
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
        "acoustic": {"free_field_distance_m": 10.0, "directionality_factor": 2.0},
        "norm": {"uni_en_14511_version": "UNI EN 14511 - 2022"},
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


def _catalog() -> tuple[dict[str, object], ...]:
    return tuple(o.to_dict() for o in MockOptionsCatalog().list_options("PLP", "HS", "052"))


def _context(**overrides: object) -> GenerationContext:
    values: dict[str, object] = {
        "record": _record(),
        "contacts": _contacts(),
        "catalog_options": _catalog(),
        "selected_option_codes": ("1", "B", "C"),
        "project_name": "Projet COURNEUVE",
        "generated_at": _NOW,
        "document_reference": "INV-TEST",
    }
    values.update(overrides)
    return GenerationContext(**values)  # type: ignore[arg-type]


def test_cover_carries_project_machine_and_edition() -> None:
    html = render_html(_context())
    assert "Projet COURNEUVE" in html
    assert 'class="model">PLP <b>052</b>' in html
    assert "Pompe à chaleur réversible air / eau" in html
    assert "Édition du 16 novembre 2026" in html
    assert "INV-TEST" in html
    assert "A000CE000I00110" in html


def test_cover_falls_back_to_machine_without_project_name() -> None:
    html = render_html(_context(project_name="   "))
    assert "Sélection PLP 052" in html
    assert "Projet COURNEUVE" not in html


def test_contents_lists_sections_with_their_page_numbers() -> None:
    html = render_html(_context())
    assert '<a href="#synthese"><span class="n">01</span><span class="t">Synthèse de la sélection</span><span class="p">03</span></a>' in html
    assert '<span class="t">Vos contacts France Air</span>' in html
    # Every page carries its own folio: no cross-reference left to resolve.
    assert "target-counter" not in html


def test_synthesis_formats_numbers_the_french_way() -> None:
    html = render_html(_context())
    assert "41,7" in html and "52,3" in html
    assert "3,37" in html
    # Energy balance: 41.7 kW extracted + 16.6 kW electricity = 58.3 kW rejected.
    assert "58,3 kW" in html
    # Heating: 52.3 kW delivered = 15.5 kW electricity + 36.8 kW from the air.
    assert "36,8 kW" in html
    assert '<span class="on">A++</span>' in html


def test_acoustic_rows_extrapolate_from_the_sound_power() -> None:
    html = render_html(_context())
    # Lp = 83 + 10 log(2 / 4 pi r^2): 61 dB(A) at 5 m, 49 dB(A) at 20 m.
    assert "61 dB(A)" in html
    assert "55 dB(A)" in html
    assert "49 dB(A)" in html


def test_options_page_lists_the_whole_catalogue_by_family() -> None:
    html = render_html(_context())
    assert "Hydraulique" in html and "Régulation et communication" in html
    assert "Pompe à eau côté utilisateur" in html
    assert "Carte Ethernet + horloge" in html  # available, not selected
    assert html.count(">Retenue</td>") == 3
    assert "Catalogue GALLETTI · 3 retenues sur 10" in html


def test_options_fall_back_to_decoded_record_options_without_catalogue() -> None:
    html = render_html(_context(catalog_options=(), selected_option_codes=()))
    assert "Protection echangeur" in html
    assert "Options décodées de la désignation" in html
    # Undecoded designation placeholders never reach the client document.
    assert "B1P00" not in html


def test_selected_pump_is_reported_in_the_technical_data() -> None:
    html = render_html(_context())
    assert "Pompe simple basse pression (retenue)" in html
    assert "à confirmer avec le référentiel GALLETTI" in html


def test_pump_values_come_from_the_catalogue_when_known() -> None:
    catalog = list(_catalog())
    pump = next(o for o in catalog if o["code"] == "1")
    catalog[catalog.index(pump)] = {**pump, "current_A": 2.1, "available_pressure_kPa": 120.0}
    html = render_html(_context(catalog_options=tuple(catalog)))
    assert "2,1 A" in html and "120 kPa" in html
    assert "à confirmer avec le référentiel GALLETTI" not in html


def test_range_documentation_feeds_description_and_implantation() -> None:
    html = render_html(_context())
    assert "Descriptif de la machine" in html
    assert "Compresseur scroll à technologie inverter." in html
    assert "Zone de sécurité R290 (D)" in html
    assert "Points de vigilance R290" in html
    assert "Support dimensionné pour la masse de la machine : 500 kg." in html


def test_unknown_range_skips_the_documented_sections() -> None:
    record = _record()
    record["model"] = "ZZZ"
    html = render_html(_context(record=record))
    assert "Descriptif de la machine" not in html
    assert 'id="implantation"' not in html
    assert "Synthèse de la sélection" in html


def test_chiller_without_heating_mode() -> None:
    record = copy.deepcopy(_record())
    record["family"] = "GEG"
    record["type"] = "CS"
    record["performance"]["heating"] = {}  # type: ignore[index]
    html = render_html(_context(record=record))
    assert "Mode chauffage non applicable" in html
    assert "Groupe d’eau glacée air / eau" in html
    assert "EER · SEER" in html
    assert "Classe d’efficacité saisonnière" not in html


def test_contacts_page_highlights_the_department_on_the_map() -> None:
    html = render_html(_context())
    assert "Département <b>69 · Rhône</b>" in html
    assert 'fill="#032d59" stroke="#ffffff"' in html  # the highlighted department
    assert "Camille Durand" in html and "CD" in html


def test_contacts_page_is_skipped_without_contacts() -> None:
    html = render_html(_context(contacts=None))
    assert 'id="contacts"' not in html
    assert "Vos contacts France Air" not in html


def test_missing_values_render_as_a_dash() -> None:
    record = _record()
    record["general"]["refrigerant"] = None  # type: ignore[index]
    html = render_html(_context(record=record))
    assert "— · 3" in html


def test_internal_warnings_stay_out_of_the_client_document() -> None:
    record = _record()
    record["warnings"] = [
        {"code": "designation_decoder_missing", "field": "options", "message": "Set me up"}
    ]
    html = render_html(_context(record=record))
    assert "designation_decoder_missing" not in html


def test_html_is_self_contained() -> None:
    html = render_html(_context())
    assert "data:font/woff2;base64," in html
    assert "data:image/webp;base64," in html
    assert "file://" not in html and "http://" not in html.replace(
        "http://www.w3.org/2000/svg", ""
    )


_TINY_PNG_DATA_URL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgAAIA"
    "AAUAAarVyFEAAAAASUVORK5CYII="
)


def test_plans_section_has_one_sheet_per_attached_drawing() -> None:
    html = render_html(
        _context(
            plans=(
                PlanImage(name="Vue de face", data_url=_TINY_PNG_DATA_URL),
                PlanImage(name="Vue de dessus", data_url=_TINY_PNG_DATA_URL),
            )
        )
    )
    assert html.count('id="plans"') == 1
    assert 'href="#plans"' in html
    assert "Vue de face" in html and "Vue de dessus" in html


def test_plans_section_is_skipped_without_drawings() -> None:
    html = render_html(_context())
    assert 'id="plans"' not in html
    assert 'href="#plans"' not in html


def test_render_pdf_returns_pdf_bytes() -> None:
    pdf = render_pdf(_context())
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 1000


def test_render_pdf_with_plans_returns_pdf_bytes() -> None:
    pdf = render_pdf(_context(plans=(PlanImage(name="Plan", data_url=_TINY_PNG_DATA_URL),)))
    assert pdf.startswith(b"%PDF-")


def test_render_pdf_raises_when_weasyprint_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "weasyprint":
            raise ImportError("not installed in this test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(PdfEngineUnavailableError):
        render_pdf(GenerationContext(record=_record()))


def test_render_pdf_raises_when_system_libraries_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "weasyprint":
            raise OSError("cannot load library 'libpango-1.0-0'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(PdfEngineUnavailableError):
        render_pdf(GenerationContext(record=_record()))


def test_minimal_record_still_renders() -> None:
    html = render_html(GenerationContext(record={"model": "PLP", "size": "052", "type": "HS"}))
    assert "Synthèse de la sélection" in html


def test_suggested_filename_slugifies_machine_identity() -> None:
    assert suggested_filename(_record()) == "INVENIO-plp-052-hs.pdf"
    assert suggested_filename({}, "html") == "INVENIO-fiche.html"
    assert (
        suggested_filename(_record(), project_name="Projet Courneuve é")
        == "INVENIO-projet-courneuve-e-plp-052-hs.pdf"
    )
