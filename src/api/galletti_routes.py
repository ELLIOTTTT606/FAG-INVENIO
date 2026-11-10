"""Endpoints FastAPI pour le configurateur GALLETTI (Phase 1).

Exposent la liste des projets GALLETTI et le détail d'un projet, à partir du
client ``GallettiSelectorClient``. L'authentification se fait par cookie de
session (variable d'env ``GALLETTI_COOKIE``) ; sans elle, les endpoints
renvoient 503 avec un message clair plutôt que de planter.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, Response

from src.services.galletti_client import (
    GallettiAuthError,
    GallettiError,
    GallettiSelectorClient,
    make_client_from_env,
    results_to_canonical,
)
from src.services.pdf_generator import (
    GenerationContext,
    PdfEngineUnavailableError,
    render_html,
    render_pdf,
    suggested_filename,
)
from src.services.settings import get_settings

router = APIRouter(prefix="/galletti", tags=["galletti"])


@lru_cache(maxsize=1)
def _client() -> GallettiSelectorClient:
    return make_client_from_env()


@router.get("/status", summary="GALLETTI connectivity diagnostic for the UI badge")
def galletti_status() -> dict[str, Any]:
    settings = get_settings()
    has_cookie = bool(settings.galletti_cookie)
    has_user = bool(settings.galletti_user)
    has_password = bool(settings.galletti_password)
    if has_user and has_password:
        mode = "login"
    elif has_cookie:
        mode = "cookie"
    else:
        mode = "none"
    return {
        "configured": settings.galletti_live,
        "base_url": settings.galletti_base_url,
        # Diagnostic (booléens seulement, aucune valeur de secret exposée)
        "mode": mode,
        "has_cookie": has_cookie,
        "has_user": has_user,
        "has_password": has_password,
    }


@router.get("/projects", summary="Liste les projets (offerte) du compte GALLETTI")
def list_projects() -> dict[str, Any]:
    try:
        projects = _client().list_projects()
    except GallettiAuthError as err:
        raise HTTPException(status_code=503, detail=str(err)) from err
    except GallettiError as err:
        raise HTTPException(status_code=502, detail=str(err)) from err
    return {"projects": [p.to_dict() for p in projects]}


@router.get("/projects/{project_id}", summary="Détail d'un projet (ses articles)")
def get_project(project_id: int) -> dict[str, Any]:
    try:
        detail = _client().get_project(project_id)
    except GallettiAuthError as err:
        raise HTTPException(status_code=503, detail=str(err)) from err
    except GallettiError as err:
        raise HTTPException(status_code=502, detail=str(err)) from err
    return {
        "id": detail.id,
        "articles": [a.to_dict() for a in detail.articles],
    }


@router.get(
    "/projects/{project_id}/fiche",
    summary="Génère la fiche INVENIO d'un modèle d'un projet (HTML ou PDF)",
)
def generate_fiche(
    project_id: int,
    family: str = Query(..., min_length=1, description="Famille GALLETTI, ex. 'GAL|PLE HS'"),
    model: str = Query(..., min_length=1, description="Modèle, ex. 'PLE062HS'"),
    size: str = Query("", description="Taille (optionnel)"),
    type_: str = Query("HS", alias="type", description="Type machine (HS/HL/CS/CL)"),
    fmt: str = Query("html", alias="format", pattern="^(html|pdf)$"),
) -> Response:
    try:
        results = _client().get_results(family=family, model=model, project_id=project_id)
    except GallettiAuthError as err:
        raise HTTPException(status_code=503, detail=str(err)) from err
    except GallettiError as err:
        raise HTTPException(status_code=502, detail=str(err)) from err

    record = results_to_canonical(results, family=family, size=size, type_=type_)
    context = GenerationContext(record=record)

    if fmt == "pdf":
        try:
            pdf_bytes = render_pdf(context)
        except PdfEngineUnavailableError as err:
            raise HTTPException(
                status_code=503,
                detail="Moteur PDF indisponible. Installez weasyprint pour le PDF.",
            ) from err
        filename = suggested_filename(record)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{filename}"'},
        )

    return HTMLResponse(content=render_html(context), status_code=200)
