"""Endpoints FastAPI pour la pré-analyse de demande (CCTP / mail) — Phase 2.

Accepte du texte collé OU un fichier (TXT/PDF/DOCX), en extrait le texte, puis
l'envoie au LLM agnostique pour produire une analyse structurée.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException, UploadFile
from pydantic import BaseModel, Field

from src.services.demand_analyzer import analyze_demand
from src.services.llm_client import LLMError, LLMNotConfiguredError, make_llm_from_env
from src.services.settings import get_settings

router = APIRouter(prefix="/analyze", tags=["analyze"])

MAX_ANALYZE_BYTES = 10 * 1024 * 1024  # 10 MB


class AnalyzeTextRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Texte de la demande (mail, note, CCTP)")


def _extract_text_from_upload(file: UploadFile, content: bytes) -> str:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix in ("", ".txt", ".md"):
        for enc in ("utf-8", "latin-1"):
            try:
                return content.decode(enc)
            except UnicodeDecodeError:
                continue
        return content.decode("utf-8", errors="replace")
    if suffix == ".docx":
        from docx import Document

        doc = Document(io.BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs if p.text)
    if suffix == ".pdf":
        from pdfminer.high_level import extract_text

        return extract_text(io.BytesIO(content)) or ""
    raise HTTPException(
        status_code=415,
        detail=f"Type de fichier non supporté : {suffix!r}. Utilisez TXT, PDF ou DOCX.",
    )


def _run_analysis(text: str) -> dict[str, Any]:
    try:
        return analyze_demand(text, llm=make_llm_from_env())
    except LLMNotConfiguredError as err:
        raise HTTPException(status_code=503, detail=str(err)) from err
    except LLMError as err:
        raise HTTPException(status_code=502, detail=str(err)) from err


@router.get("/status", summary="Diagnostic de configuration du moteur d'analyse (LLM)")
def analyze_status() -> dict[str, Any]:
    s = get_settings()
    return {
        "configured": s.llm_live,
        "base_url": s.llm_base_url,
        "model": s.llm_model,
        "has_api_key": bool(s.llm_api_key),
    }


@router.post("/text", summary="Analyse une demande fournie en texte")
def analyze_text(payload: AnalyzeTextRequest = Body(...)) -> dict[str, Any]:
    return _run_analysis(payload.text)


@router.post("/file", summary="Analyse une demande fournie en fichier (TXT/PDF/DOCX)")
async def analyze_file(file: UploadFile) -> dict[str, Any]:
    content = file.file.read()
    if len(content) > MAX_ANALYZE_BYTES:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux (max 10 MB).")
    text = _extract_text_from_upload(file, content)
    if not text.strip():
        raise HTTPException(status_code=422, detail="Aucun texte extractible du fichier.")
    result = _run_analysis(text)
    result["_meta"] = {**result.get("_meta", {}), "filename": file.filename}
    return result
