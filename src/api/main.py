"""FastAPI application for INVENIO."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, UploadFile

from src.parser.docx_parser import parse_docx
from src.parser.pdf_parser import parse_pdf

app = FastAPI(
    title="INVENIO API",
    version="0.2.0",
    description="France Air - Migration GALLETTI -> INVENIO. Endpoints MVP.",
)

MAX_UPLOAD_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB


@app.get("/health", summary="Liveness probe")
def health() -> dict[str, str]:
    return {"status": "ok"}


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
