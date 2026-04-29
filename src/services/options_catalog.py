"""Repository abstraction for the OPTIONS et ACCESSOIRES catalog.

Two implementations:
  - `MockOptionsCatalog` returns a small but realistic catalog so the UI
    works without Baserow.
  - `BaserowOptionsCatalog` queries Baserow table 941070, filtered by
    (model, type, size).

`make_catalog_from_env()` picks the right one based on env vars; the
FastAPI route depends on the abstract type and tests inject a fake.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from src.services.baserow_client import BaserowClient, BaserowConfig


@dataclass(frozen=True)
class CatalogOption:
    code: str
    category: str
    label: str
    description: str | None = None
    tips: str | None = None
    price_eur: float | None = None
    available: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "category": self.category,
            "label": self.label,
            "description": self.description,
            "tips": self.tips,
            "price_eur": self.price_eur,
            "available": self.available,
        }


class OptionsCatalog(ABC):
    @abstractmethod
    def list_options(self, model: str, type_: str, size: str) -> list[CatalogOption]: ...


# ---------------------------------------------------------------------------
# Mock implementation
# ---------------------------------------------------------------------------


_PAC_OPTIONS: tuple[CatalogOption, ...] = (
    CatalogOption("0", "Pompe eau cote utilisateur", "Absente", "Aucune pompe integree."),
    CatalogOption(
        "1",
        "Pompe eau cote utilisateur",
        "Pompe simple basse pression",
        "Pompe simple non modulante 230V.",
        tips="Verifier la pression disponible avant installation.",
    ),
    CatalogOption(
        "2",
        "Pompe eau cote utilisateur",
        "Pompe haute pression",
        "Pompe simple haute pression pour reseau dense.",
    ),
    CatalogOption(
        "P",
        "Kit antigel",
        "Protection echangeur + pompe",
        "Resistance electrique + traceur thermique.",
        tips="Recommande en climat froid (T < -5 degC).",
    ),
    CatalogOption(
        "B",
        "Reservoir tampon",
        "Ballon 125 L",
        "Reservoir d'eau integre 125 L pour stabiliser la regulation.",
    ),
    CatalogOption(
        "C",
        "Communication",
        "Carte RS485 Modbus",
        "Carte de communication Modbus RTU pour GTC.",
        tips="Compatible avec la GTC France Air.",
    ),
    CatalogOption(
        "E",
        "Communication",
        "Carte Ethernet + horloge",
        "Carte Ethernet + supervision web embarquee.",
    ),
    CatalogOption("S", "Acoustique", "Version standard", "Configuration acoustique standard."),
    CatalogOption(
        "L",
        "Acoustique",
        "Version low-noise",
        "Capot acoustique additionnel et ventilateurs basse vitesse.",
    ),
    CatalogOption(
        "I",
        "Reglage",
        "Vanne d'expansion electronique",
        "Detendeur electronique pilotee par la regulation.",
    ),
)

_GEG_OPTIONS: tuple[CatalogOption, ...] = (
    CatalogOption("0", "Pompe eau cote utilisateur", "Absente", "Aucune pompe integree."),
    CatalogOption(
        "1",
        "Pompe eau cote utilisateur",
        "Pompe simple basse pression",
        "Pompe simple non modulante 400V.",
    ),
    CatalogOption(
        "2",
        "Pompe eau cote utilisateur",
        "Pompe haute pression",
        "Pompe simple haute pression pour reseau dense.",
    ),
    CatalogOption(
        "B",
        "Reservoir tampon",
        "Ballon 250 L",
        "Reservoir d'eau integre 250 L pour stabiliser la regulation.",
    ),
    CatalogOption(
        "C",
        "Communication",
        "Carte RS485 Modbus",
        "Carte de communication Modbus RTU pour GTC.",
    ),
    CatalogOption(
        "E",
        "Communication",
        "Carte Ethernet",
        "Carte Ethernet pour supervision web.",
    ),
    CatalogOption(
        "R",
        "Recuperation de chaleur",
        "Recuperation partielle",
        "Echangeur dedie pour recuperation de chaleur (~20%).",
        tips="Necessite un circuit hydraulique secondaire.",
    ),
    CatalogOption("S", "Acoustique", "Version standard", "Configuration acoustique standard."),
    CatalogOption(
        "L",
        "Acoustique",
        "Version low-noise",
        "Capot acoustique additionnel et ventilateurs basse vitesse.",
    ),
)


class MockOptionsCatalog(OptionsCatalog):
    """Family-aware mock catalog (PAC / GEG) ignoring model/size variation."""

    def list_options(self, model: str, type_: str, size: str) -> list[CatalogOption]:
        del model, size  # unused in the mock
        if type_.startswith("H"):
            return list(_PAC_OPTIONS)
        if type_.startswith("C"):
            return list(_GEG_OPTIONS)
        # Unknown type: return the common subset so the UI still has data.
        common_codes = {"0", "1", "B", "C", "E", "S", "L"}
        return [opt for opt in _PAC_OPTIONS if opt.code in common_codes]


# ---------------------------------------------------------------------------
# Baserow implementation
# ---------------------------------------------------------------------------


def _first_str(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value:
            return str(value).strip()
    return ""


def _parse_float(raw: Any) -> float | None:
    if raw in (None, ""):
        return None
    try:
        return float(str(raw).replace(",", "."))
    except ValueError:
        return None


def _parse_bool(raw: Any) -> bool:
    if isinstance(raw, bool):
        return raw
    if raw in (None, ""):
        return True  # default to available when the column is missing
    return str(raw).strip().lower() in {"1", "true", "yes", "oui", "vrai"}


def _row_to_option(row: dict[str, Any]) -> CatalogOption | None:
    label = _first_str(row, "label_fr", "label", "Libelle")
    code = _first_str(row, "option_code", "code", "Code")
    if not (label and code):
        return None
    return CatalogOption(
        code=code,
        category=_first_str(row, "option_category", "category", "Categorie") or "Autres",
        label=label,
        description=_first_str(row, "description_fr", "description", "Description") or None,
        tips=_first_str(row, "tips_fr", "tips", "Tips") or None,
        price_eur=_parse_float(row.get("price_eur") or row.get("price") or row.get("Prix")),
        available=_parse_bool(row.get("available") or row.get("Disponible")),
    )


def _row_matches(row: dict[str, Any], model: str, type_: str, size: str) -> bool:
    row_model = _first_str(row, "model", "model_type", "Modele").upper()
    row_type = _first_str(row, "type", "Type").upper()
    row_size = _first_str(row, "size", "Taille").upper()
    if row_model and model and row_model != model.upper() and not row_model.startswith(model.upper()):
        return False
    if row_type and type_ and row_type != type_.upper() and row_type[:1] != type_[:1]:
        return False
    return not (row_size and size and row_size != size.upper())


class BaserowOptionsCatalog(OptionsCatalog):
    def __init__(self, client: BaserowClient, table_id: int) -> None:
        self._client = client
        self._table_id = table_id

    def list_options(self, model: str, type_: str, size: str) -> list[CatalogOption]:
        catalog: list[CatalogOption] = []
        for row in self._client.iter_all_rows(self._table_id):
            if not _row_matches(row, model, type_, size):
                continue
            option = _row_to_option(row)
            if option is None:
                continue
            catalog.append(option)
        return catalog


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def make_catalog_from_env() -> OptionsCatalog:
    token = (os.environ.get("BASEROW_TOKEN") or "").strip()
    url = (os.environ.get("BASEROW_URL") or "").strip()
    table_id = int(os.environ.get("BASEROW_TABLE_OPTIONS_ACCESSOIRES", "0") or "0")
    if not token or not url or not table_id:
        return MockOptionsCatalog()
    config = BaserowConfig(base_url=url, token=token)
    return BaserowOptionsCatalog(client=BaserowClient(config), table_id=table_id)
