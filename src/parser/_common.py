"""Shared logic for the DOCX and PDF parsers.

The two parsers differ only in how they obtain the (paragraph_text, table_rows)
sequence from the source file. Once that sequence is produced, this module
takes care of:
  - section tracking (Refroidissement / Chauffage / Donnees acoustiques /
    UNI EN 14511 / Donnees generales),
  - performance vs conditions disambiguation,
  - fuzzy mapping of `(label, unit, value)` triples to canonical paths,
  - unit coercion,
  - family inference (PAC vs GEG),
  - building the canonical empty payload.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz, process

PARSER_VERSION = "0.3.0"

DESIGNATION_RE = re.compile(
    r"(?P<model>[A-Z]{2,5})(?P<size>\d{2,3})(?P<heatcool>[HC])(?P<acoustic>[SL])"
    r"(?:[A-Z0-9]*)"
    r"(?:\s+(?P<block1>[A-Z0-9]{6,30}))?"
    r"(?:\s+(?P<block2>[A-Z0-9]{6,30}))?"
)

SECTION_HEADERS: list[tuple[str, str]] = [
    ("conditions_cooling", "refroidissement"),
    ("conditions_cooling", "cooling"),
    ("conditions_heating", "chauffage"),
    ("conditions_heating", "heating"),
    ("acoustic", "donnees pour calcul niveau sonore"),
    ("acoustic", "donnees acoustiques"),
    ("norm", "uni en 14511"),
    ("norm", "norme uni en 14511"),
    ("general", "donnees generales"),
    ("general", "common data"),
]

PERFORMANCE_MARKERS = (
    "data inputs",
    "puissance frigorifique",
    "puissance de refroidissement",
    "puissance calorifique",
    "puissance de chauffage",
)


@dataclass
class MappingRule:
    section: str
    source_label: str
    canonical_path: str
    unit: str
    coercion: str  # float1 | float2 | int | string | bool


@dataclass
class ParseResult:
    data: dict[str, Any]
    warnings: list[dict[str, str]] = field(default_factory=list)


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def normalize_label(label: str) -> str:
    label = strip_accents(label.lower())
    label = re.sub(r"[^a-z0-9]+", " ", label)
    return " ".join(label.split())


def load_mapping(mapping_path: Path) -> list[MappingRule]:
    rules: list[MappingRule] = []
    with mapping_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rules.append(
                MappingRule(
                    section=(row.get("section") or "*").strip(),
                    source_label=row["source_label"].strip(),
                    canonical_path=row["canonical_path"].strip(),
                    unit=row.get("unit", "").strip(),
                    coercion=(row.get("coercion") or "string").strip() or "string",
                )
            )
    return rules


def index_rules(rules: list[MappingRule]) -> dict[str, dict[str, MappingRule]]:
    index: dict[str, dict[str, MappingRule]] = defaultdict(dict)
    for rule in rules:
        index[rule.section][normalize_label(rule.source_label)] = rule
    return index


def coerce(raw: str, coercion: str) -> Any:
    raw = (raw or "").strip().replace(",", ".")
    if raw == "" or raw.lower() in {"n/a", "na", "-"}:
        return None

    if coercion == "string":
        return raw

    if coercion == "bool":
        token = normalize_label(raw)
        if token in {"oui", "yes", "true", "1"}:
            return True
        if token in {"non", "no", "false", "0"}:
            return False
        return None

    digits = re.sub(r"[^0-9.\-]+", "", raw)
    if digits in {"", "-", ".", "-.", ".-"}:
        return None
    try:
        if coercion == "int":
            return int(round(float(digits)))
        if coercion == "float1":
            return round(float(digits), 1)
        if coercion == "float2":
            return round(float(digits), 2)
    except ValueError:
        return None
    return raw


def detect_designation(paragraphs: list[str]) -> tuple[str | None, dict[str, str] | None]:
    for line in paragraphs:
        match = DESIGNATION_RE.search(line)
        if match:
            return match.group(0), match.groupdict()
    return None, None


def set_path(target: dict[str, Any], dotted_path: str, value: Any) -> None:
    parts = dotted_path.split(".")
    cursor = target
    for part in parts[:-1]:
        cursor = cursor.setdefault(part, {})
    cursor[parts[-1]] = value


def detect_section(text: str, current: str | None) -> str | None:
    norm = normalize_label(text)
    if not norm:
        return current
    for section, marker in SECTION_HEADERS:
        if marker in norm:
            return section
    return current


def is_performance_context(text: str) -> bool:
    norm = normalize_label(text)
    return any(marker in norm for marker in PERFORMANCE_MARKERS)


def resolve_section(base_section: str | None, performance_context: bool) -> str | None:
    if base_section in {"conditions_cooling", "conditions_heating"} and performance_context:
        return (
            "performance_cooling"
            if base_section == "conditions_cooling"
            else "performance_heating"
        )
    return base_section


def match_label(
    norm_label: str,
    rules_by_section: dict[str, dict[str, MappingRule]],
    section: str | None,
    *,
    threshold: int = 80,
) -> MappingRule | None:
    if not norm_label:
        return None
    candidates: dict[str, MappingRule] = {}
    if section and section in rules_by_section:
        candidates.update(rules_by_section[section])
    candidates.update(rules_by_section.get("*", {}))
    if not candidates:
        return None
    match = process.extractOne(norm_label, list(candidates.keys()), scorer=fuzz.WRatio)
    if not match:
        return None
    candidate, score, _ = match
    if score < threshold:
        return None
    return candidates[candidate]


def empty_payload(filename: str, *, fmt: str) -> dict[str, Any]:
    return {
        "family": "PAC",
        "model": "",
        "size": "",
        "type": "HS",
        "designation_code": None,
        "conditions": {},
        "performance": {},
        "hydraulics": {},
        "acoustic": {},
        "norm": {},
        "general": {},
        "options": [],
        "contacts": {},
        "source": {
            "filename": filename,
            "format": fmt,
            "extracted_at": datetime.now(tz=UTC).isoformat(),
            "parser_version": PARSER_VERSION,
        },
        "warnings": [],
    }


def has_any_value(node: Any) -> bool:
    if isinstance(node, dict):
        return any(has_any_value(v) for v in node.values())
    if isinstance(node, list):
        return any(has_any_value(v) for v in node)
    return node is not None and node != ""


def process_table_rows(
    rows: list[list[str]],
    *,
    base_section: str | None,
    rules_by_section: dict[str, dict[str, MappingRule]],
    data: dict[str, Any],
    warnings: list[dict[str, str]],
) -> str | None:
    """Walk the rows of one table; mutate `data` and `warnings`. Return updated section."""

    if not rows:
        return base_section

    table_text = " ".join(cell for row in rows for cell in row)
    if base_section is None:
        base_section = detect_section(table_text, base_section)
    performance_context = is_performance_context(table_text)
    section_for_lookup = resolve_section(base_section, performance_context)

    for row_index, row in enumerate(rows):
        if not row:
            continue
        first_cell = row[0]
        is_header_row = all(not (c or "").strip() for c in row[1:])
        if is_header_row:
            new_section = detect_section(first_cell, base_section)
            if new_section != base_section:
                base_section = new_section
                section_for_lookup = resolve_section(base_section, performance_context)
            continue
        if len(row) < 2 or not first_cell:
            continue

        value_cell = row[-1]
        unit_cell = row[1] if len(row) >= 3 else ""
        rule = match_label(normalize_label(first_cell), rules_by_section, section_for_lookup)
        if rule is None:
            continue

        coerced = coerce(value_cell, rule.coercion)
        if coerced is None and value_cell.strip() != "":
            warnings.append(
                {
                    "code": "coercion_failed",
                    "message": (
                        f"Could not coerce value {value_cell!r} for label {first_cell!r} "
                        f"(section={section_for_lookup}, row={row_index})."
                    ),
                    "field": rule.canonical_path,
                }
            )
            continue
        if (
            rule.unit
            and unit_cell
            and normalize_label(unit_cell) != normalize_label(rule.unit)
        ):
            warnings.append(
                {
                    "code": "unit_mismatch",
                    "message": (
                        f"Unit {unit_cell!r} does not match expected {rule.unit!r} "
                        f"for {rule.canonical_path}."
                    ),
                    "field": rule.canonical_path,
                }
            )
        set_path(data, rule.canonical_path, coerced)

    return base_section


def infer_family(data: dict[str, Any], warnings: list[dict[str, str]]) -> None:
    type_first = (data.get("type") or "")[:1]
    has_heating = has_any_value(data.get("performance", {}).get("heating"))

    if type_first == "H":
        family = "PAC"
    elif type_first == "C":
        family = "GEG"
    else:
        family = "PAC" if has_heating else "GEG"

    if family == "PAC" and not has_heating:
        warnings.append(
            {
                "code": "family_mismatch",
                "message": "Designation looks like PAC but no heating performance data was found.",
                "field": "family",
            }
        )
    if family == "GEG" and has_heating:
        warnings.append(
            {
                "code": "family_mismatch",
                "message": "Designation looks like GEG but heating performance data was extracted.",
                "field": "family",
            }
        )

    data["family"] = family


def populate_designation(data: dict[str, Any], paragraphs: list[str], warnings: list[dict[str, str]]) -> None:
    designation_code, parts = detect_designation(paragraphs)
    data["designation_code"] = designation_code
    if parts:
        data["model"] = parts.get("model") or ""
        data["size"] = parts.get("size") or ""
        heatcool = parts.get("heatcool") or "H"
        acoustic = parts.get("acoustic") or "S"
        data["type"] = f"{heatcool}{acoustic}"
    else:
        warnings.append(
            {
                "code": "designation_not_found",
                "message": "Designation code not found in document text.",
                "field": "designation_code",
            }
        )
