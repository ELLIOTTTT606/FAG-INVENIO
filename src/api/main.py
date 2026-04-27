"""FastAPI application skeleton for INVENIO."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, UploadFile

from src.parser.docx_parser import parse_docx

app = FastAPI(
    title="INVENIO API",
    version="0.1.0",
    description="France Air - Migration GALLETTI -> INVENIO. Endpoints MVP.",
)

ALLOWED_EXTENSIONS = {".docx"}
MAX_UPLOAD_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB


@app.get("/health", summary="Liveness probe")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/parse/docx",
    summary="Parse a GALLETTI DOCX file and return canonical JSON",
)
async def parse_docx_endpoint(file: UploadFile) -> dict[str, Any]:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type {suffix!r}. Allowed: {sorted(ALLOWED_EXTENSIONS)}.",
        )

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds max size of {MAX_UPLOAD_SIZE_BYTES} bytes.",
        )

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
        tmp.write(content)
        tmp.flush()
        result = parse_docx(tmp.name)

    return {"data": result.data, "warnings": result.warnings}
