"""Tests for the OptionsCatalog repository (Mock + Baserow impl)."""

from __future__ import annotations

import httpx

from src.services.baserow_client import BaserowClient, BaserowConfig
from src.services.options_catalog import (
    BaserowOptionsCatalog,
    CatalogOption,
    MockOptionsCatalog,
)


def test_mock_catalog_returns_pac_options_for_h_type() -> None:
    catalog = MockOptionsCatalog()
    options = catalog.list_options(model="PLP", type_="HS", size="052")
    categories = {opt.category for opt in options}
    assert "Pompe eau cote utilisateur" in categories
    assert "Kit antigel" in categories  # PAC-specific
    assert "Reservoir tampon" in categories
    assert any(opt.code == "P" for opt in options)


def test_mock_catalog_returns_geg_options_for_c_type() -> None:
    catalog = MockOptionsCatalog()
    options = catalog.list_options(model="VLS", type_="CS", size="202")
    categories = {opt.category for opt in options}
    assert "Recuperation de chaleur" in categories  # GEG-specific
    # No "Kit antigel" -> not in GEG mock data
    assert "Kit antigel" not in categories


def test_mock_catalog_returns_common_subset_for_unknown_type() -> None:
    catalog = MockOptionsCatalog()
    options = catalog.list_options(model="XXX", type_="ZZ", size="000")
    codes = {opt.code for opt in options}
    assert "0" in codes
    assert "1" in codes
    # Family-specific options excluded
    assert "P" not in codes  # PAC kit antigel
    assert "R" not in codes  # GEG heat recovery


def test_catalog_option_to_dict_round_trip() -> None:
    option = CatalogOption(
        code="1",
        category="Pompe",
        label="Simple",
        description="desc",
        tips="tip",
        price_eur=129.0,
        available=True,
    )
    payload = option.to_dict()
    assert payload == {
        "code": "1",
        "category": "Pompe",
        "label": "Simple",
        "description": "desc",
        "tips": "tip",
        "price_eur": 129.0,
        "available": True,
    }


def _baserow(transport: httpx.MockTransport) -> BaserowClient:
    config = BaserowConfig(base_url="https://baserow.test", token="dummy")
    return BaserowClient(
        config,
        client=httpx.Client(
            base_url=config.base_url, headers=config.headers, transport=transport
        ),
    )


def test_baserow_catalog_filters_by_model_type_size() -> None:
    rows = [
        {
            "model": "PLP",
            "type": "HS",
            "size": "052",
            "option_code": "P",
            "option_category": "Kit antigel",
            "label_fr": "Protection echangeur",
            "description_fr": "Resistance",
            "tips_fr": "",
            "price_eur": "120.00",
            "available": "true",
        },
        {
            "model": "VLS",
            "type": "CS",
            "size": "202",
            "option_code": "R",
            "option_category": "Recuperation de chaleur",
            "label_fr": "Recup partielle",
        },
    ]

    def handle(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": rows, "next": None})

    catalog = BaserowOptionsCatalog(client=_baserow(httpx.MockTransport(handle)), table_id=1)
    matches = catalog.list_options(model="PLP", type_="HS", size="052")
    assert [opt.code for opt in matches] == ["P"]
    assert matches[0].price_eur == 120.0
    assert matches[0].available is True


def test_baserow_catalog_falls_back_to_first_letter_of_type() -> None:
    """A row of family `H` should match `HS` and `HL` queries."""

    rows = [
        {
            "model": "PLP",
            "type": "H",
            "size": "052",
            "option_code": "C",
            "option_category": "Communication",
            "label_fr": "Modbus",
        }
    ]

    def handle(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": rows, "next": None})

    catalog = BaserowOptionsCatalog(client=_baserow(httpx.MockTransport(handle)), table_id=1)
    matches = catalog.list_options(model="PLP", type_="HL", size="052")
    assert [opt.code for opt in matches] == ["C"]


def test_baserow_catalog_skips_rows_without_label_or_code() -> None:
    rows = [
        {"model": "PLP", "type": "HS", "size": "052", "option_code": "1"},
        {"model": "PLP", "type": "HS", "size": "052", "label_fr": "Orphan label"},
        {
            "model": "PLP",
            "type": "HS",
            "size": "052",
            "option_code": "2",
            "label_fr": "Pompe HP",
        },
    ]

    def handle(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": rows, "next": None})

    catalog = BaserowOptionsCatalog(client=_baserow(httpx.MockTransport(handle)), table_id=1)
    matches = catalog.list_options(model="PLP", type_="HS", size="052")
    assert [opt.code for opt in matches] == ["2"]
