"""HTML + PDF rendering of the INVENIO selection fiche.

`src.services.fiche.view` turns the canonical record (plus the project name,
the options catalogue, the chosen options, the contacts and the attached
plans) into fixed A4 pages; the Jinja template places them. The HTML output
is self-contained (fonts and images embedded) so it can be served as an
in-app preview, printed by the browser, or piped through WeasyPrint.

WeasyPrint is an optional dependency. If it is missing, `render_pdf`
raises `PdfEngineUnavailableError` so the API can return 503 instead of 500.
"""

from __future__ import annotations

import base64
import io
import re
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

import jinja2

from src.services.fiche.resources import asset_data_url
from src.services.fiche.view import FicheInputs, Plan, build_view

__all__ = [
    "GenerationContext",
    "PdfEngineUnavailableError",
    "PlanImage",
    "render_html",
    "render_pdf",
    "suggested_filename",
]


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
    project_name: str | None = None
    # Options catalogue of the machine (CatalogOption.to_dict() entries).
    catalog_options: tuple[dict[str, Any], ...] = ()


_CORNER_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 60" preserveAspectRatio="none">'
    b'<polygon points="0,60 60,0 60,60" fill="#eef2f6"/>'
    b'<polygon points="16,60 60,16 60,60" fill="#032d59"/></svg>'
)


@lru_cache(maxsize=1)
def _environment() -> jinja2.Environment:
    return jinja2.Environment(
        loader=jinja2.PackageLoader("src.services.fiche", "templates"),
        autoescape=jinja2.select_autoescape(default=True, default_for_string=True),
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=jinja2.StrictUndefined,
    )


@lru_cache(maxsize=1)
def _images() -> dict[str, str]:
    return {
        "franceair": asset_data_url("logo-franceair.png"),
        "franceair_white": asset_data_url("logo-franceair-blanc.png"),
        "invenio": asset_data_url("logo-invenio.png"),
        "invenio_white": asset_data_url("logo-invenio-blanc.png"),
        "corner": "data:image/svg+xml;base64," + base64.b64encode(_CORNER_SVG).decode("ascii"),
    }


@lru_cache(maxsize=1)
def _stylesheet() -> str:
    fonts = {weight: asset_data_url(f"montserrat-{weight}.woff2") for weight in (300, 400, 500, 600)}
    return _environment().get_template("fiche.css.j2").render(fonts=fonts, images=_images())


def _slugify(value: str) -> str:
    folded = "".join(
        c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c)
    )
    return re.sub(r"[^A-Za-z0-9-]+", "-", folded).strip("-").lower()


def build_inputs(context: GenerationContext) -> FicheInputs:
    record = context.record
    reference = (
        context.document_reference
        or f"INV-{record.get('model', '')}{record.get('size', '')}-{uuid.uuid4().hex[:6].upper()}"
    )
    return FicheInputs(
        record=record,
        generated_at=context.generated_at or datetime.now(tz=UTC),
        document_reference=reference,
        project_name=context.project_name,
        contacts=context.contacts,
        catalog_options=tuple(context.catalog_options),
        selected_option_codes=tuple(context.selected_option_codes),
        plans=tuple(Plan(name=p.name, data_url=p.data_url) for p in context.plans),
    )


def render_html(context: GenerationContext) -> str:
    """Render the fiche as a self-contained HTML string."""

    view = build_view(build_inputs(context))
    photo_name = view["cover"]["photo"]
    photo = asset_data_url(photo_name) if photo_name else None
    return (
        _environment()
        .get_template("fiche.html.j2")
        .render(v=view, images=_images(), photo=photo, stylesheet=_stylesheet())
    )


def render_pdf(context: GenerationContext) -> bytes:
    """Render the fiche as a PDF byte string (requires WeasyPrint)."""

    try:
        from weasyprint import HTML
    except (ImportError, OSError) as err:  # pragma: no cover - environment-dependent
        # ImportError: the package is absent. OSError: it is installed but its
        # system libraries (Pango, GObject) cannot be loaded, as on serverless
        # hosts.
        raise PdfEngineUnavailableError(
            "WeasyPrint is unavailable: not installed, or its system libraries "
            "(Pango) are missing on this host."
        ) from err

    html = render_html(context)
    buffer = io.BytesIO()
    HTML(string=html).write_pdf(buffer)
    return buffer.getvalue()


def suggested_filename(
    record: dict[str, Any], extension: str = "pdf", project_name: str | None = None
) -> str:
    parts = [
        project_name or "",
        record.get("model") or "",
        record.get("size") or "",
        record.get("type") or "",
    ]
    base = "-".join(str(part).strip() for part in parts if str(part).strip()) or "fiche"
    return f"INVENIO-{_slugify(base) or 'fiche'}.{extension}"
