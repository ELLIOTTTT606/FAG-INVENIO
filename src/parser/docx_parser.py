"""DOCX parser for INVENIO.

Walks the document body in order (paragraphs and tables interleaved) and
hands each (paragraph_text or table_rows) chunk to the section-aware
extraction logic in `src.parser._common`.
"""

from __future__ import annotations

import io
import json
import re
import sys
import zipfile
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


def _open_docx_safe(path: Path | str) -> DocxDocument:
    """Ouvre un DOCX en nettoyant les médias manquants dans le ZIP."""
    with open(path, "rb") as f:
        raw = f.read()

    # Lire le ZIP original
    src_zip = zipfile.ZipFile(io.BytesIO(raw), "r")
    names = set(src_zip.namelist())

    # Reconstruire un ZIP propre sans les entrées cassées
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as dst_zip:
        for item in src_zip.infolist():
            data = src_zip.read(item.filename)

            # Nettoyer les fichiers .rels : supprimer les refs vers médias inexistants
            if item.filename.endswith(".rels"):
                # Dossier de base depuis lequel les Target relatifs sont résolus
                base = "/".join(item.filename.split("/")[:-2])

                def keep_rel(match: re.Match[str], base: str = base) -> str:
                    target = re.search(r'Target="([^"]+)"', match.group(0))
                    if not target:
                        return match.group(0)
                    t = target.group(1).lstrip("/")
                    full = f"{base}/{t}".lstrip("/") if base else t
                    if full not in names and t not in names:
                        return ""
                    return match.group(0)

                try:
                    text = data.decode("utf-8")
                    text = re.sub(r"<Relationship[^/]*/>", keep_rel, text)
                    data = text.encode("utf-8")
                except Exception:  # noqa: BLE001 - .rels illisible : on garde l'original
                    pass

            dst_zip.writestr(item, data)

    src_zip.close()
    buf.seek(0)
    return Document(buf)


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

    document = _open_docx_safe(path)
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
