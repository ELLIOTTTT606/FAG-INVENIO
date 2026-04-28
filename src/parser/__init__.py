"""DOCX / PDF parsers producing the INVENIO canonical JSON."""

from src.parser.docx_parser import parse_docx
from src.parser.pdf_parser import parse_pdf

__all__ = ["parse_docx", "parse_pdf"]
