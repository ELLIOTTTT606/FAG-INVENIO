"""FastAPI application for INVENIO."""

from __future__ import annotations

import re
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, UploadFile
from fastapi import Path as PathParam
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field

from src.parser.docx_parser import parse_docx
from src.parser.pdf_parser import parse_pdf
from src.services.contacts_repo import ContactsRepository, make_repository_from_env
from src.services.options_catalog import OptionsCatalog, make_catalog_from_env
from src.services.pdf_generator import (
    GenerationContext,
    PdfEngineUnavailableError,
    render_html,
    render_pdf,
    suggested_filename,
)
from src.services.settings import get_settings

app = FastAPI(
    title="INVENIO API",
    version="0.3.0",
    description="France Air - Migration GALLETTI -> INVENIO. Endpoints MVP.",
)

MAX_UPLOAD_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB
DEPARTMENT_RE = re.compile(r"^(2A|2B|[0-9]{2,3})$")


@lru_cache(maxsize=1)
def get_contacts_repository() -> ContactsRepository:
    return make_repository_from_env()


@lru_cache(maxsize=1)
def get_options_catalog() -> OptionsCatalog:
    return make_catalog_from_env()


@app.get("/health", summary="Liveness probe")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/admin/baserow-status", summary="Baserow connectivity diagnostic for the UI badge")
def baserow_status() -> dict[str, Any]:
    settings = get_settings()
    return {
        "mode": settings.baserow_mode,
        "url": settings.baserow_url,
        "tables": {
            "clients": settings.baserow_table_clients,
            "contacts_force_vente": settings.baserow_table_contacts_force_vente,
            "contacts_solution": settings.baserow_table_contacts_solution,
            "options_accessoires": settings.baserow_table_options_accessoires,
        },
    }


def _parse_upload(file: UploadFile, allowed_suffix: str) -> dict[str, Any]:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix != allowed_suffix:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type {suffix!r}. Expected {allowed_suffix!r}.",
        )

    content = file.file.read()
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds max size of {MAX_UPLOAD_SIZE_BYTES} bytes.",
        )

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
        tmp.write(content)
        tmp.flush()
        result = parse_docx(tmp.name) if allowed_suffix == ".docx" else parse_pdf(tmp.name)

    return {"data": result.data, "warnings": result.warnings}


@app.post(
    "/parse/docx",
    summary="Parse a GALLETTI DOCX file and return canonical JSON",
)
async def parse_docx_endpoint(file: UploadFile) -> dict[str, Any]:
    return _parse_upload(file, ".docx")


@app.post(
    "/parse/pdf",
    summary="Parse a GALLETTI native PDF and return canonical JSON",
)
async def parse_pdf_endpoint(file: UploadFile) -> dict[str, Any]:
    return _parse_upload(file, ".pdf")


@app.get(
    "/clients/search",
    summary="Autocomplete clients by name, code, or postal code (>=2 chars)",
)
def search_clients(
    q: str = Query(..., min_length=0, description="Free-text query."),
    limit: int = Query(10, ge=1, le=50),
    repo: ContactsRepository = Depends(get_contacts_repository),
) -> list[dict[str, str]]:
    return [c.to_dict() for c in repo.search_clients(q, limit=limit)]


@app.get(
    "/contacts/department/{department}",
    summary="TCI / TCS / Solution Habitat for a given department code",
)
def contacts_for_department(
    department: str = PathParam(..., description="Code department, e.g. '69', '2A'"),
    repo: ContactsRepository = Depends(get_contacts_repository),
) -> dict[str, Any]:
    if not DEPARTMENT_RE.match(department):
        raise HTTPException(
            status_code=400, detail=f"Invalid department code: {department!r}."
        )
    return repo.get_contacts_for_department(department).to_dict()


class GenerationRequest(BaseModel):
    """Payload sent by the UI to render the fiche."""

    record: dict[str, Any] = Field(..., description="Canonical record from /parse/*")
    contacts: dict[str, Any] | None = None
    selected_option_codes: list[str] = Field(default_factory=list)
    document_reference: str | None = None


def _build_generation_context(payload: GenerationRequest) -> GenerationContext:
    return GenerationContext(
        record=payload.record,
        contacts=payload.contacts,
        selected_option_codes=tuple(payload.selected_option_codes),
        document_reference=payload.document_reference,
    )


@app.post(
    "/generate/preview",
    summary="Render the fiche as a self-contained HTML preview",
    response_class=HTMLResponse,
)
def generate_preview(payload: GenerationRequest) -> HTMLResponse:
    html = render_html(_build_generation_context(payload))
    return HTMLResponse(content=html, status_code=200)


@app.post(
    "/generate/pdf",
    summary="Render the fiche as a PDF (requires WeasyPrint)",
)
def generate_pdf_endpoint(payload: GenerationRequest) -> Response:
    try:
        pdf_bytes = render_pdf(_build_generation_context(payload))
    except PdfEngineUnavailableError as err:
        raise HTTPException(
            status_code=503,
            detail="PDF engine unavailable. Install weasyprint to enable /generate/pdf.",
        ) from err

    filename = suggested_filename(payload.record)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get(
    "/options",
    summary="Catalog of options/accessories for a given (model, type, size)",
)
def options_for_machine(
    model: str = Query(..., min_length=1),
    type: str = Query(..., min_length=1, description="HS / HL / CS / CL"),
    size: str = Query(..., min_length=1),
    catalog: OptionsCatalog = Depends(get_options_catalog),
) -> dict[str, Any]:
    options = catalog.list_options(model=model, type_=type, size=size)
    return {
        "model": model,
        "type": type,
        "size": size,
        "options": [opt.to_dict() for opt in options],
    }
