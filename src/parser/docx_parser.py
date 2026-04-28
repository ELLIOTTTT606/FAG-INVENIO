"""DOCX parser for INVENIO.

Walks the document body in order (paragraphs and tables interleaved) and
hands each (paragraph_text or table_rows) chunk to the section-aware
extraction logic in `src.parser._common`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from docx import Document
from docx.document import Document as DocxDocument
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from src.parser._common import (
    DESIGNATION_RE,
    PARSER_VERSION,
    ParseResult,
    detect_designation,
    detect_section,
    empty_payload,
    index_rules,
    infer_family,
    load_mapping,
    normalize_label,
    populate_designation,
    process_table_rows,
)

__all__ = [
    "DESIGNATION_RE",
    "PARSER_VERSION",
    "ParseResult",
    "detect_designation",
    "normalize_label",
    "parse_docx",
]


def _iter_block_items(parent: DocxDocument) -> list[Paragraph | Table]:
    body = parent.element.body
    items: list[Paragraph | Table] = []
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            items.append(Paragraph(child, parent))
        elif child.tag == qn("w:tbl"):
            items.append(Table(child, parent))
    return items


def _extract_table_rows(table: Table) -> list[list[str]]:
    return [[cell.text.strip() for cell in row.cells] for row in table.rows]


def parse_docx(
    path: Path | str,
    mapping_path: Path | str | None = None,
    *,
    decoder_path: Path | str | None = None,
) -> ParseResult:
    path = Path(path)
    if mapping_path is None:
        mapping_path = Path(__file__).parent / "mapping.csv"
    if decoder_path is None:
        decoder_path = Path(__file__).parent / "designation_decoder.csv"
    rules_by_section = index_rules(load_mapping(Path(mapping_path)))

    document = Document(str(path))
    data = empty_payload(path.name, fmt="docx")
    warnings: list[dict[str, str]] = data["warnings"]

    paragraphs = [p.text for p in document.paragraphs if p.text and p.text.strip()]
    populate_designation(data, paragraphs, warnings, decoder_path=Path(decoder_path))

    base_section: str | None = None
    for item in _iter_block_items(document):
        if isinstance(item, Paragraph):
            text = item.text or ""
            if text.strip():
                base_section = detect_section(text, base_section)
        else:
            base_section = process_table_rows(
                _extract_table_rows(item),
                base_section=base_section,
                rules_by_section=rules_by_section,
                data=data,
                warnings=warnings,
            )

    infer_family(data, warnings)
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
