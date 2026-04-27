"""Minimal DOCX parser for INVENIO MVP.

Extracts simple 2-3 column tables (label / unit / value), detects the
GALLETTI designation string, and produces a partial canonical JSON.

Limitations (signaled as warnings):
  - merged cells
  - embedded images / scanned content
  - multi-line cell content beyond single value tokens
"""

from __future__ import annotations

import csv
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from docx import Document
from rapidfuzz import fuzz, process

PARSER_VERSION = "0.1.0"

# Designation: e.g. "PLP052HS2B A000CE000I00110 0000000I000000000000"
DESIGNATION_RE = re.compile(
    r"(?P<model>[A-Z]{2,5})(?P<size>\d{2,3})(?P<heatcool>[HC])(?P<acoustic>[SL])"
    r"(?:[A-Z0-9]*)"
    r"(?:\s+(?P<block1>[A-Z0-9]{6,30}))?"
    r"(?:\s+(?P<block2>[A-Z0-9]{6,30}))?"
)

UNIT_TO_CANONICAL: dict[str, float] = {
    "kPa": 1.0,
    "mCE": 9.80665,
    "kW": 1.0,
    "W": 0.001,
    "A": 1.0,
    "%": 1.0,
    "C": 1.0,
    "l/h": 1.0,
    "dB(A)": 1.0,
}


@dataclass
class MappingRule:
    source_label: str
    canonical_path: str
    unit: str
    coercion: str  # "float1" | "int" | "string"


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
                    source_label=row["source_label"].strip(),
                    canonical_path=row["canonical_path"].strip(),
                    unit=row.get("unit", "").strip(),
                    coercion=row.get("coercion", "string").strip() or "string",
                )
            )
    return rules


def _coerce(raw: str, coercion: str) -> Any:
    raw = (raw or "").strip().replace(",", ".")
    if raw == "" or raw.lower() in {"n/a", "na", "-"}:
        return None
    if coercion == "string":
        return raw
    digits = re.sub(r"[^0-9.\-]+", "", raw)
    if digits in {"", "-", ".", "-.", ".-"}:
        return None
    try:
        if coercion == "int":
            return int(round(float(digits)))
        if coercion == "float1":
            return round(float(digits), 1)
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


def _match_label(
    norm_label: str, rules: list[MappingRule], threshold: int = 80
) -> MappingRule | None:
    if not norm_label:
        return None
    choices = {normalize_label(r.source_label): r for r in rules}
    match = process.extractOne(norm_label, choices.keys(), scorer=fuzz.WRatio)
    if not match:
        return None
    candidate, score, _ = match
    if score < threshold:
        return None
    return choices[candidate]


def _extract_table_rows(table: Any) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in table.rows:
        cells = [cell.text.strip() for cell in row.cells]
        rows.append(cells)
    return rows


def parse_docx(path: Path | str, mapping_path: Path | str | None = None) -> ParseResult:
    path = Path(path)
    if mapping_path is None:
        mapping_path = Path(__file__).parent / "mapping.csv"
    rules = load_mapping(Path(mapping_path))

    document = Document(str(path))

    paragraphs = [p.text for p in document.paragraphs if p.text and p.text.strip()]
    designation_code, parts = detect_designation(paragraphs)

    data: dict[str, Any] = {
        "family": "PAC",
        "model": "",
        "size": "",
        "type": "HS",
        "designation_code": designation_code,
        "performance": {},
        "conditions": {},
        "hydraulics": {},
        "electrical": {},
        "acoustics": {},
        "options": [],
        "contacts": {},
        "source": {
            "filename": path.name,
            "format": "docx",
            "extracted_at": datetime.now(tz=UTC).isoformat(),
            "parser_version": PARSER_VERSION,
        },
        "warnings": [],
    }

    if parts:
        data["model"] = parts.get("model") or ""
        data["size"] = parts.get("size") or ""
        heatcool = parts.get("heatcool") or "H"
        acoustic = parts.get("acoustic") or "S"
        data["type"] = f"{heatcool}{acoustic}"

    warnings: list[dict[str, str]] = []
    if not designation_code:
        warnings.append(
            {
                "code": "designation_not_found",
                "message": "Designation code not found in document text.",
                "field": "designation_code",
            }
        )

    for table in document.tables:
        rows = _extract_table_rows(table)
        for row_index, row in enumerate(rows):
            if len(row) < 2:
                continue
            label = row[0]
            if not label:
                continue
            value_cell = row[-1]
            unit_cell = row[1] if len(row) >= 3 else ""
            rule = _match_label(normalize_label(label), rules)
            if rule is None:
                continue
            coerced = _coerce(value_cell, rule.coercion)
            if coerced is None and value_cell.strip() != "":
                warnings.append(
                    {
                        "code": "coercion_failed",
                        "message": (
                            f"Could not coerce value {value_cell!r} for label {label!r} "
                            f"(row {row_index})."
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
