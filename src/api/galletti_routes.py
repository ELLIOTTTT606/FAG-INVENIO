"""Endpoints FastAPI pour le configurateur GALLETTI (Phase 1).

Exposent la liste des projets GALLETTI et le détail d'un projet, à partir du
client ``GallettiSelectorClient``. L'authentification se fait par cookie de
session (variable d'env ``GALLETTI_COOKIE``) ; sans elle, les endpoints
renvoient 503 avec un message clair plutôt que de planter.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from fastapi import APIRouter, HTTPException

from src.services.galletti_client import (
    GallettiAuthError,
    GallettiError,
    GallettiSelectorClient,
    make_client_from_env,
)
from src.services.settings import get_settings

router = APIRouter(prefix="/galletti", tags=["galletti"])


@lru_cache(maxsize=1)
def _client() -> GallettiSelectorClient:
    return make_client_from_env()


@router.get("/status", summary="GALLETTI connectivity diagnostic for the UI badge")
def galletti_status() -> dict[str, Any]:
    settings = get_settings()
    return {
        "configured": settings.galletti_live,
        "base_url": settings.galletti_base_url,
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
