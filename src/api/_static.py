"""
src/api/_static.py
──────────────────
Monte le frontend React pré-buildé en tant que fichiers statiques.

En développement : ce module ne fait rien (ui/dist/ n'existe pas,
le proxy Vite prend en charge le routage).

En production (image Docker) : ui/dist/ est présent, FastAPI sert
le bundle et gère le routage SPA via le catch-all final.

Usage — ajouter en TOUTE FIN de src/api/main.py, après tous les
routers/endpoints API :

    from src.api._static import mount_frontend
    mount_frontend(app)

L'ordre est crucial : les routes API enregistrées avant le mount()
ont toujours la priorité sur le catch-all SPA.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

_DIST = Path(__file__).resolve().parent.parent.parent / "ui" / "dist"


def mount_frontend(app: FastAPI) -> None:
    """Monte ui/dist/ comme frontend statique si le build existe."""
    if not _DIST.is_dir():
        # Mode dev : Vite tourne séparément sur :5173
        return

    # Ressources hachées (JS, CSS) — cachables longtemps
    assets_dir = _DIST / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="ui-assets")

    # Fichiers racine (favicon, robots.txt, manifest…)
    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon() -> FileResponse:
        f = _DIST / "favicon.ico"
        if f.is_file():
            return FileResponse(f)
        return FileResponse(_DIST / "index.html")

    # ── Catch-all SPA — doit être le DERNIER handler enregistré ──
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str) -> FileResponse:
        """
        Toute URL inconnue renvoie index.html pour que React Router
        gère le routage côté client.
        """
        candidate = _DIST / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_DIST / "index.html")
