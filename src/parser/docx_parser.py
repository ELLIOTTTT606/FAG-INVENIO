"""DOCX parser for INVENIO.

Walks the document body in order (paragraphs and tables interleaved), uses
header paragraphs to track the current section (Refroidissement, Chauffage,
Donnees acoustiques, UNI EN 14511, Donnees generales), and routes each
extracted (label, unit, value) row to the right canonical path via the
section-aware mapping in `mapping.csv`.

Family inference (PAC vs GEG):
  - first heuristic: the third character of the designation type letter
    (`H` -> PAC, `C` -> GEG).
  - cross-check: presence of any `performance.heating.*` value strongly
    supports PAC; absence supports GEG. A mismatch raises a warning.

Limitations (signaled as warnings):
  - merged cells / images / scanned content
  - free-text fields (descriptive sections) not yet structured
"""

from __future__ import annotations

import csv
import json
import re
import sys
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from docx import Document
from docx.document import Document as DocxDocument
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph
from rapidfuzz import fuzz, process

PARSER_VERSION = "0.2.0"

# Designation: e.g. "PLP052HS2B A000CE000I00110 0000000I000000000000"
DESIGNATION_RE = re.compile(
    r"(?P<model>[A-Z]{2,5})(?P<size>\d{2,3})(?P<heatcool>[HC])(?P<acoustic>[SL])"
    r"(?:[A-Z0-9]*)"
    r"(?:\s+(?P<block1>[A-Z0-9]{6,30}))?"
    r"(?:\s+(?P<block2>[A-Z0-9]{6,30}))?"
)


# Section detection. A header paragraph or first row of a section table that
# contains one of these snippets switches the active section. `None` means
# "do not change section" - lookups will use the most recent value.
_SECTION_HEADERS: list[tuple[str, str]] = [
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

# When inside a "performance" tableau (vs "conditions"), the canonical paths
# differ. We detect the "performance" context with these markers.
_PERFORMANCE_MARKERS = (
    "data inputs",
    "puissance frigorifique",
    "puissance de refroidissement",
    "puissance calorifique",
    "puissance de chauffage",
)


@dataclass
class MappingRule:
    section: str  # e.g. "conditions_cooling", "performance_heating", "*"
    source_label: str
    canonical_path: str
    unit: str
    coercion: str  # "float1" | "float2" | "int" | "string" | "bool"


@dataclass
class ParseResult:
    data: dict[str, Any]
    warnings: list[dict[str, str]] = field(default_factory=list)


def _strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def normalize_label(label: str) -> str:
    label = _strip_accents(label.lower())
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


def _index_rules(rules: list[MappingRule]) -> dict[str, dict[str, MappingRule]]:
    """Index rules by section -> normalized_label -> rule."""

    index: dict[str, dict[str, MappingRule]] = defaultdict(dict)
    for rule in rules:
        index[rule.section][normalize_label(rule.source_label)] = rule
    return index


def _coerce(raw: str, coercion: str) -> Any:
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


def _set_path(target: dict[str, Any], dotted_path: str, value: Any) -> None:
    parts = dotted_path.split(".")
    cursor = target
    for part in parts[:-1]:
        cursor = cursor.setdefault(part, {})
    cursor[parts[-1]] = value


def _detect_section(text: str, current: str | None) -> str | None:
    """Return a new section identifier if `text` matches a header, else current."""

    norm = normalize_label(text)
    if not norm:
        return current
    for section, marker in _SECTION_HEADERS:
        if marker in norm:
            return section
    return current


def _is_performance_context(text: str) -> bool:
    norm = normalize_label(text)
    return any(marker in norm for marker in _PERFORMANCE_MARKERS)


def _resolve_section(base_section: str | None, performance_context: bool) -> str | None:
    """Map base section + performance flag onto a mapping section key."""

    if base_section in {"conditions_cooling", "conditions_heating"} and performance_context:
        return "performance_cooling" if base_section == "conditions_cooling" else "performance_heating"
    return base_section


def _match_label(
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


def _iter_block_items(parent: DocxDocument) -> list[Paragraph | Table]:
    """Yield paragraphs and tables in body order."""

    body = parent.element.body
    items: list[Paragraph | Table] = []
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            items.append(Paragraph(child, parent))
        elif child.tag == qn("w:tbl"):
            items.append(Table(child, parent))
    return items


def _extract_table_rows(table: Table) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in table.rows:
        cells = [cell.text.strip() for cell in row.cells]
        rows.append(cells)
    return rows


def _empty_payload(filename: str) -> dict[str, Any]:
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
            "format": "docx",
            "extracted_at": datetime.now(tz=UTC).isoformat(),
            "parser_version": PARSER_VERSION,
        },
        "warnings": [],
    }


def _has_any_value(node: Any) -> bool:
    if isinstance(node, dict):
        return any(_has_any_value(v) for v in node.values())
    if isinstance(node, list):
        return any(_has_any_value(v) for v in node)
    return node is not None and node != ""


def _process_table(
    table: Table,
    *,
    base_section: str | None,
    rules_by_section: dict[str, dict[str, MappingRule]],
    data: dict[str, Any],
    warnings: list[dict[str, str]],
) -> str | None:
    """Process one table; return possibly-updated base_section."""

    rows = _extract_table_rows(table)
    if not rows:
        return base_section

    table_text = " ".join(cell for row in rows for cell in row)
    if base_section is None:
        base_section = _detect_section(table_text, base_section)
    performance_context = _is_performance_context(table_text)

    section_for_lookup = _resolve_section(base_section, performance_context)

    for row_index, row in enumerate(rows):
        if not row:
            continue
        first_cell = row[0]
        is_header_row = all(not (c or "").strip() for c in row[1:])
        if is_header_row:
            new_section = _detect_section(first_cell, base_section)
            if new_section != base_section:
                base_section = new_section
                section_for_lookup = _resolve_section(base_section, performance_context)
            continue
        if len(row) < 2 or not first_cell:
            continue

        value_cell = row[-1]
        unit_cell = row[1] if len(row) >= 3 else ""
        rule = _match_label(normalize_label(first_cell), rules_by_section, section_for_lookup)
        if rule is None:
            continue

        coerced = _coerce(value_cell, rule.coercion)
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
        _set_path(data, rule.canonical_path, coerced)

    return base_section


def _infer_family(data: dict[str, Any], warnings: list[dict[str, str]]) -> None:
    type_first = (data.get("type") or "")[:1]
    has_heating = _has_any_value(data.get("performance", {}).get("heating"))

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


def parse_docx(path: Path | str, mapping_path: Path | str | None = None) -> ParseResult:
    path = Path(path)
    if mapping_path is None:
        mapping_path = Path(__file__).parent / "mapping.csv"
    rules = load_mapping(Path(mapping_path))
    rules_by_section = _index_rules(rules)

    document = Document(str(path))

    data = _empty_payload(path.name)
    warnings = data["warnings"]

    paragraphs = [p.text for p in document.paragraphs if p.text and p.text.strip()]
    designation_code, parts = detect_designation(paragraphs)
    data["designation_code"] = designation_code
    if parts:
        data["model"] = parts.get("model") or ""
        data["size"] = parts.get("size") or ""
        heatcool = parts.get("heatcool") or "H"
        acoustic = parts.get("acoustic") or "S"
        data["type"] = f"{heatcool}{acoustic}"
    if not designation_code:
        warnings.append(
            {
                "code": "designation_not_found",
                "message": "Designation code not found in document text.",
                "field": "designation_code",
            }
        )

    base_section: str | None = None
    for item in _iter_block_items(document):
        if isinstance(item, Paragraph):
            text = item.text or ""
            if text.strip():
                base_section = _detect_section(text, base_section)
        else:  # Table
            base_section = _process_table(
                item,
                base_section=base_section,
                rules_by_section=rules_by_section,
                data=data,
                warnings=warnings,
            )

    _infer_family(data, warnings)
    data["warnings"] = warnings
    return ParseResult(data=data, warnings=warnings)


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if not args:
        print("usage: python -m src.parser.docx_parser <file.docx>", file=sys.stderr)
        return 2
    result = parse_docx(args[0])
    print(json.dumps(result.data, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
