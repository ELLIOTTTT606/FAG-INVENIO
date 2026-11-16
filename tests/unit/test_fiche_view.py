"""Tests for the fiche view model: formatting, pagination, map and computations."""

from __future__ import annotations

from datetime import UTC, datetime

from src.services.fiche import format as fmt
from src.services.fiche.resources import france_map, range_documentation
from src.services.fiche.view import FicheInputs, build_view, text_lines


def _inputs(**overrides: object) -> FicheInputs:
    values: dict[str, object] = {
        "record": {
            "family": "PAC",
            "model": "PLP",
            "size": "052",
            "type": "HS",
            "performance": {"cooling": {"power_kW": 41.7}, "heating": {"power_kW": 52.3}},
        },
        "generated_at": datetime(2026, 11, 16, tzinfo=UTC),
        "document_reference": "INV-X",
    }
    values.update(overrides)
    return FicheInputs(**values)  # type: ignore[arg-type]


def test_number_formatting() -> None:
    assert fmt.number(16259.0, "m³/h") == "16 259 m³/h"
    assert fmt.number(41.7, "kW") == "41,7 kW"
    assert fmt.number(4.15) == "4,15"
    assert fmt.number(0) == "0"
    assert fmt.number(None, "kW") == "—"
    assert fmt.number(58.3000001, "kW", 1) == "58,3 kW"
    assert fmt.supply("400 / 3+N / 50") == "400 V · 3+N · 50 Hz"


def test_long_date_is_french() -> None:
    assert fmt.long_date(datetime(2026, 2, 3)) == "3 février 2026"


def test_text_lines_wraps_on_words() -> None:
    assert text_lines("Pompe simple", 8.6, 100) == 1
    long_text = " ".join(["vanne"] * 60)
    assert text_lines(long_text, 8.6, 100) > 2
    # Bold text is wider, never narrower.
    assert text_lines(long_text, 8.6, 100, 600) >= text_lines(long_text, 8.6, 100)


def test_pages_are_numbered_and_listed_in_the_contents() -> None:
    view = build_view(_inputs())
    kinds = [page["kind"] for page in view["pages"]]
    assert kinds[:2] == ["cover", "toc"]
    assert kinds[-1] == "back"
    assert [p["number"] for p in view["pages"]] == list(range(1, len(kinds) + 1))
    for entry in view["toc"]:
        assert view["pages"][entry["page"] - 1]["kind"] == entry["kind"]


def test_long_catalogue_spreads_over_continuation_pages() -> None:
    catalog = tuple(
        {
            "code": f"X{i}",
            "category": "Communication" if i % 2 else "Pompe eau cote utilisateur",
            "label": f"Option numéro {i} avec un libellé assez long pour tenir sur une ligne",
            "description": "Description de démonstration " * 4,
        }
        for i in range(60)
    )
    view = build_view(_inputs(catalog_options=catalog, selected_option_codes=("X1", "X2")))
    options_pages = [p for p in view["pages"] if p["kind"] == "options"]
    assert len(options_pages) > 2
    assert not options_pages[0]["continued"]
    assert all(page["continued"] for page in options_pages[1:])
    rendered = [
        row["code"] for page in options_pages for block in page["data"] for row in block["rows"] if row["type"] == "opt"
    ]
    assert sorted(rendered) == sorted(o["code"] for o in catalog)
    # The contents points at the first options page; later sections follow.
    entry = next(e for e in view["toc"] if e["kind"] == "options")
    assert entry["page"] == options_pages[0]["number"]
    assert view["options_page"] == options_pages[0]["number"]


def test_unknown_categories_land_in_the_accessories_family() -> None:
    catalog = ({"code": "Z", "category": "Emballage maritime", "label": "Caisse bois"},)
    view = build_view(_inputs(catalog_options=catalog))
    options_page = next(p for p in view["pages"] if p["kind"] == "options")
    assert options_page["data"][0]["family"]["name"] == "Accessoires"


def test_map_contains_every_metropolitan_department() -> None:
    codes = {d["code"] for d in france_map()["departments"]}
    assert len(codes) == 96
    assert {"01", "2A", "2B", "69", "75", "95"} <= codes


def test_range_documentation_lookup_is_case_insensitive_and_safe() -> None:
    assert range_documentation("plp") is not None
    assert range_documentation("../PLP") is None
    assert range_documentation(None) is None


def test_clearances_only_when_known_for_the_size() -> None:
    known = build_view(_inputs(record={"model": "PLP", "size": "052", "type": "HS", "general": {"refrigerant": "R290"}}))
    other = build_view(_inputs(record={"model": "PLP", "size": "037", "type": "HS", "general": {"refrigerant": "R290"}}))
    known_page = next(p for p in known["pages"] if p["kind"] == "implantation")
    other_page = next(p for p in other["pages"] if p["kind"] == "implantation")
    assert known_page["data"]["safety_distance"] == "3 m"
    assert other_page["data"]["safety_distance"] is None
    assert "p. 15" in other_page["data"]["caption"]


def test_every_range_documentation_file_is_valid() -> None:
    import json
    from importlib import resources

    import jsonschema

    data = resources.files("src.services.fiche").joinpath("data")
    schema = json.loads(data.joinpath("gamme.schema.json").read_text("utf-8"))
    assets = resources.files("src.services.fiche").joinpath("assets")
    files = [f for f in data.joinpath("gammes").iterdir() if f.name.endswith(".json")]
    assert files, "at least one documented range"
    for entry in files:
        doc = json.loads(entry.read_text("utf-8"))
        jsonschema.validate(doc, schema)
        assert entry.name == f"{doc['model']}.json"
        if "photo" in doc:
            assert assets.joinpath(doc["photo"]).is_file(), doc["photo"]
        envelope = doc.get("envelope")
        if envelope:
            for low, high in (envelope["air_C"], envelope["water_C"]):
                assert low < high
