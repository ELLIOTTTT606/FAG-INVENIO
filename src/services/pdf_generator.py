"""HTML + PDF rendering of the INVENIO selection fiche.

The Jinja2 template (`templates/fiche.html.j2`) consumes the canonical
record produced by the parsers, plus a few view-model extras (selected
options, contacts, references). The HTML output is self-contained
(stylesheet inlined) so it can either be served as-is for an in-app
preview or piped through WeasyPrint to produce the final PDF.

WeasyPrint is an optional dependency. If it is missing, `render_pdf`
raises `PdfEngineUnavailableError` so the API can return 503 instead of 500.
"""

from __future__ import annotations

import io
import re
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import resources
from typing import Any

import jinja2

__all__ = [
    "GenerationContext",
    "PdfEngineUnavailableError",
    "PlanImage",
    "render_html",
    "render_pdf",
]


_TEMPLATES_PACKAGE = "src.services.templates"


class PdfEngineUnavailableError(RuntimeError):
    """Raised when WeasyPrint (the PDF engine) is not importable."""


@dataclass(frozen=True)
class PlanImage:
    """An attached drawing (plan / dimensions / 3D view) for the PDF section."""

    name: str
    data_url: str  # full data URL: "data:image/png;base64,..."


@dataclass(frozen=True)
class GenerationContext:
    """Inputs needed by the template, in addition to the canonical record."""

    record: dict[str, Any]
    contacts: dict[str, Any] | None = None
    selected_option_codes: tuple[str, ...] = ()
    document_reference: str | None = None
    generated_at: datetime | None = None
    plans: tuple[PlanImage, ...] = ()


def _load_text(name: str) -> str:
    return resources.files(_TEMPLATES_PACKAGE).joinpath(name).read_text(encoding="utf-8")


def _load_static(name: str) -> str:
    return resources.files(_TEMPLATES_PACKAGE).joinpath("static").joinpath(name).read_text(
        encoding="utf-8"
    )


def _format_value(value: Any, unit: str | None = None) -> str:
    if value is None or value == "":
        return '<span class="missing">Donnée non disponible</span>'
    if isinstance(value, bool):
        text = "Oui" if value else "Non"
    elif isinstance(value, float):
        text = f"{value:.1f}".rstrip("0").rstrip(".") or "0"
        if "." not in text and value != int(value):
            text = f"{value:.1f}"
    else:
        text = str(value)
    return f"{text} {unit}" if unit else text


def _slugify(value: str) -> str:
    folded = "".join(
        c
        for c in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(c)
    )
    return re.sub(r"[^A-Za-z0-9-]+", "-", folded).strip("-").lower()


def _select_options(record: dict[str, Any], selected_codes: tuple[str, ...]) -> list[dict[str, Any]]:
    """Return the option entries from the record that match the user's selection.

    Falls back to options whose `selected` flag is True when no explicit
    code list is given.
    """

    options = record.get("options") or []
    if selected_codes:
        wanted = set(selected_codes)
        return [opt for opt in options if opt.get("code") in wanted]
    return [opt for opt in options if opt.get("selected")]


def _build_environment() -> jinja2.Environment:
    loader = jinja2.PackageLoader(_TEMPLATES_PACKAGE, ".")
    env = jinja2.Environment(
        loader=loader,
        autoescape=jinja2.select_autoescape(default=True),
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=jinja2.ChainableUndefined,
    )
    env.globals["value"] = _format_value
    return env


def render_html(context: GenerationContext) -> str:
    """Render the fiche as a self-contained HTML string."""

    env = _build_environment()
    template = env.get_template("fiche.html.j2")
    generated_at = context.generated_at or datetime.now(tz=UTC)
    record = context.record
    selected = _select_options(record, context.selected_option_codes)

    document_reference = (
        context.document_reference
        or f"INV-{record.get('model', '')}{record.get('size', '')}-{uuid.uuid4().hex[:6].upper()}"
    )

    return template.render(
        record=record,
        warnings=record.get("warnings") or [],
        contacts=context.contacts,
        selected_options=selected,
        document_reference=document_reference,
        generated_at_fr=generated_at.strftime("%d-%m-%Y"),
        plans=[{"name": plan.name, "data_url": plan.data_url} for plan in context.plans],
        stylesheet=_load_static("style.css"),
    )


def render_pdf(context: GenerationContext) -> bytes:
    """Render the fiche as a PDF byte string (requires WeasyPrint)."""

    try:
        from weasyprint import HTML
    except ImportError as err:  # pragma: no cover - environment-dependent
        raise PdfEngineUnavailableError(
            "WeasyPrint is not installed. Run `pip install -e .[pdf]`."
        ) from err

    html = render_html(context)
    buffer = io.BytesIO()
    HTML(string=html).write_pdf(buffer)
    return buffer.getvalue()


def suggested_filename(record: dict[str, Any], extension: str = "pdf") -> str:
    parts = [
        record.get("model") or "",
        record.get("size") or "",
        record.get("type") or "",
    ]
    base = "-".join(part for part in parts if part) or "fiche"
    return f"INVENIO-{_slugify(base) or 'fiche'}.{extension}"
