"""PDF parser for INVENIO (native, text-based PDFs).

Uses pdfplumber to extract:
  - free text per page (paragraphs),
  - tables per page (with pdfplumber's lattice-based extractor first,
    then a fallback that tries text alignment).

The extracted (paragraphs, tables) sequence is then handed to the same
section-aware logic as the DOCX parser (`src.parser._common`).

Limitations (signaled as warnings):
  - scanned / image-only PDFs (no extractable text) -> raises
    `pdf_no_text` warning; an OCR pass is out of scope for this MVP.
  - exotic table layouts (no lines, irregular spacing) may yield empty
    tables; pdfplumber's heuristics handle the GALLETTI fixture.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pdfplumber
from pdfplumber.page import Page
from pdfplumber.table import Table as PlumberTable

from src.parser._common import (
    ParseResult,
    detect_section,
    empty_payload,
    index_rules,
    infer_family,
    load_mapping,
    populate_designation,
    process_table_rows,
)

__all__ = ["parse_pdf"]


_TABLE_SETTINGS_LATTICE: dict[str, Any] = {
    "vertical_strategy": "lines",
    "horizontal_strategy": "lines",
    "intersection_y_tolerance": 5,
    "intersection_x_tolerance": 5,
}

_TABLE_SETTINGS_TEXT: dict[str, Any] = {
    "vertical_strategy": "text",
    "horizontal_strategy": "text",
    "snap_tolerance": 5,
    "join_tolerance": 5,
}


def _clean_cell(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def _find_tables(page: Page) -> list[PlumberTable]:
    tables = page.find_tables(table_settings=_TABLE_SETTINGS_LATTICE)
    if not tables:
        tables = page.find_tables(table_settings=_TABLE_SETTINGS_TEXT)
    return list(tables or [])


def _table_rows(table: PlumberTable) -> list[list[str]]:
    rows = []
    for row in table.extract():
        cleaned = [_clean_cell(c) for c in row]
        if any(cell for cell in cleaned):
            rows.append(cleaned)
    return rows


def _y_in_any_bbox(y: float, bboxes: list[tuple[float, float, float, float]]) -> bool:
    return any(top - 1 <= y <= bottom + 1 for _, top, _, bottom in bboxes)


@dataclass
class _ParagraphItem:
    y: float
    text: str


@dataclass
class _TableItem:
    y: float
    rows: list[list[str]]


def _ordered_page_items(page: Page) -> tuple[list[_ParagraphItem | _TableItem], bool]:
    """Return paragraph + table items sorted top-to-bottom for one page."""

    tables = _find_tables(page)
    bboxes: list[tuple[float, float, float, float]] = [t.bbox for t in tables]

    items: list[_ParagraphItem | _TableItem] = []
    has_text = False
    for line in page.extract_text_lines() or []:
        text = (line.get("text") or "").strip()
        if not text:
            continue
        has_text = True
        y_top = float(line.get("top", 0.0))
        if _y_in_any_bbox(y_top, bboxes):
            continue  # this line is inside a table, will be captured via the table itself
        items.append(_ParagraphItem(y=y_top, text=text))

    for table in tables:
        rows = _table_rows(table)
        if not rows:
            continue
        items.append(_TableItem(y=float(table.bbox[1]), rows=rows))

    items.sort(key=lambda item: item.y)
    return items, has_text


def parse_pdf(path: Path | str, mapping_path: Path | str | None = None) -> ParseResult:
    path = Path(path)
    if mapping_path is None:
        mapping_path = Path(__file__).parent / "mapping.csv"
    rules_by_section = index_rules(load_mapping(Path(mapping_path)))

    data = empty_payload(path.name, fmt="pdf")
    warnings: list[dict[str, str]] = data["warnings"]

    all_paragraphs: list[str] = []
    base_section: str | None = None
    page_had_text = False

    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            items, has_text = _ordered_page_items(page)
            page_had_text = page_had_text or has_text
            for item in items:
                if isinstance(item, _ParagraphItem):
                    all_paragraphs.append(item.text)
                    base_section = detect_section(item.text, base_section)
                else:
                    base_section = process_table_rows(
                        item.rows,
                        base_section=base_section,
                        rules_by_section=rules_by_section,
                        data=data,
                        warnings=warnings,
                    )

    if not page_had_text:
        warnings.append(
            {
                "code": "pdf_no_text",
                "message": "PDF appears to be image-only; OCR is required for extraction.",
                "field": "source",
            }
        )

    populate_designation(data, all_paragraphs, warnings)
    infer_family(data, warnings)
    data["warnings"] = warnings
    return ParseResult(data=data, warnings=warnings)


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if not args:
        print("usage: python -m src.parser.pdf_parser <file.pdf>", file=sys.stderr)
        return 2
    result = parse_pdf(args[0])
    print(json.dumps(result.data, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
