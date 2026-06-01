"""
src/services/nocodb_client.py
─────────────────────────────
Client NocoDB — remplace BaserowClient avec la même interface publique.

NocoDB est le remplaçant open-source self-hosted de Baserow.
Son API v2 est différente mais ce client expose exactement les mêmes
méthodes que BaserowClient, donc zéro changement dans les repos
(contacts_repo.py, options_catalog.py, etc.).

Configuration (.env) :
    NOCODB_URL=http://nocodb:8080
    NOCODB_TOKEN=<token généré dans NocoDB → Team & Auth → API Tokens>
    NOCODB_TABLE_CLIENTS=md_xxx...
    NOCODB_TABLE_CONTACTS_FORCE_VENTE=md_xxx...
    NOCODB_TABLE_CONTACTS_SOLUTION=md_xxx...
    NOCODB_TABLE_OPTIONS_ACCESSOIRES=md_xxx...
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import httpx


class NoCODBError(Exception):
    """Erreur remontée par le client NocoDB."""


_RETRY_STATUS = {429, 500, 502, 503, 504}


@dataclass
class NoCODBConfig:
    base_url: str                        # ex: http://nocodb:8080
    token: str                           # xc-token
    timeout: float = 30.0
    max_retries: int = 3
    backoff_initial_seconds: float = 0.5
    backoff_factor: float = 2.0


class NoCODBClient:
    """
    Client HTTP NocoDB avec retry exponentiel et cache TTL.

    Interface identique à BaserowClient — les repos existants
    (contacts_repo, options_catalog) n'ont pas besoin de changer.

    API NocoDB v2 utilisée :
        GET  /api/v2/tables/{tableId}/records
        POST /api/v2/tables/{tableId}/records
        PATCH /api/v2/tables/{tableId}/records/{rowId}
    """

    def __init__(self, config: NoCODBConfig) -> None:
        self._config = config
        self._client = httpx.Client(
            base_url=config.base_url.rstrip("/"),
            headers={
                "xc-token": config.token,
                "Content-Type": "application/json",
            },
            timeout=config.timeout,
        )
        # Cache simple en mémoire (TTL 60s)
        self._cache: dict[tuple[Any, ...], tuple[float, Any]] = {}
        self._cache_ttl = 60.0

    # ── Interface publique (identique à BaserowClient) ──────────

    def list_rows(
        self,
        table_id: str,
        *,
        page: int = 1,
        size: int = 25,
        search: str | None = None,
        search_field: str | None = None,
    ) -> dict[str, Any]:
        """
        Liste les lignes d'une table.

        Retourne un dict compatible Baserow :
          { "count": N, "results": [...], "next": None, "previous": None }
        """
        cache_key = (table_id, page, size, search, search_field)
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        params: dict[str, Any] = {
            "limit": size,
            "offset": (page - 1) * size,
        }

        # NocoDB v2 : filtre "where=(champ,like,%valeur%)"
        if search and search_field:
            params["where"] = f"({search_field},like,%{search}%)"
        elif search:
            # Recherche multi-champ (NocoDB ne supporte pas nativement,
            # on fait une recherche basique sur le premier champ visible)
            params["where"] = f"(Title,like,%{search}%)"

        response = self._request("GET", f"/api/v2/tables/{table_id}/records", params=params)
        data = response.json()

        # Normalisation → format Baserow
        result: dict[str, Any] = {
            "count": data.get("pageInfo", {}).get("totalRows", len(data.get("list", []))),
            "results": data.get("list", []),
            "next": None,
            "previous": None,
        }

        self._cache_set(cache_key, result)
        return result

    def create_row(
        self,
        table_id: str,
        payload: dict[str, Any],
        *,
        user_field_names: bool = True,
    ) -> dict[str, Any]:
        """Crée une ligne dans la table."""
        response = self._request(
            "POST",
            f"/api/v2/tables/{table_id}/records",
            json=payload,
        )
        self._cache_invalidate(table_id)
        return response.json()

    def create_rows(
        self,
        table_id: str,
        payloads: list[dict[str, Any]],
        *,
        user_field_names: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Batch-create des lignes.
        NocoDB accepte un array JSON directement.
        """
        if not payloads:
            return []

        # NocoDB plafonne à 100 items par batch (vs 200 pour Baserow)
        results: list[dict[str, Any]] = []
        for i in range(0, len(payloads), 100):
            chunk = payloads[i : i + 100]
            response = self._request(
                "POST",
                f"/api/v2/tables/{table_id}/records",
                json=chunk,
            )
            data = response.json()
            if isinstance(data, list):
                results.extend(data)
            elif isinstance(data, dict):
                results.append(data)

        self._cache_invalidate(table_id)
        return results

    def update_row(
        self,
        table_id: str,
        row_id: int,
        payload: dict[str, Any],
        *,
        user_field_names: bool = True,
    ) -> dict[str, Any]:
        """
        Met à jour une ligne existante.
        NocoDB v2 : PATCH avec Id dans le body.
        """
        response = self._request(
            "PATCH",
            f"/api/v2/tables/{table_id}/records",
            json={"Id": row_id, **payload},
        )
        self._cache_invalidate(table_id)
        return response.json()

    def ping(self) -> bool:
        """Vérifie que le token et l'URL sont valides."""
        try:
            resp = self._request("GET", "/api/v1/health")
            return resp.status_code < 400
        except NoCODBError:
            return False

    # ── Internals ───────────────────────────────────────────────

    def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        attempts = self._config.max_retries + 1
        last_exc: Exception | None = None
        for attempt in range(attempts):
            try:
                resp = self._client.request(method, url, **kwargs)
            except httpx.HTTPError as exc:
                last_exc = exc
            else:
                if resp.status_code not in _RETRY_STATUS:
                    if resp.is_error:
                        raise NoCODBError(
                            f"NocoDB {method} {url} → {resp.status_code}: {resp.text[:200]}"
                        )
                    return resp
                last_exc = NoCODBError(f"HTTP {resp.status_code}")

            if attempt + 1 < attempts:
                delay = self._config.backoff_initial_seconds * (
                    self._config.backoff_factor ** attempt
                )
                time.sleep(min(delay, 8.0))

        raise NoCODBError(f"NocoDB {method} {url} a échoué après {attempts} tentatives") \
            from last_exc

    # ── Cache ────────────────────────────────────────────────────

    def _cache_get(self, key: tuple[Any, ...]) -> Any | None:
        entry = self._cache.get(key)
        if entry is None:
            return None
        ts, value = entry
        if time.monotonic() - ts > self._cache_ttl:
            del self._cache[key]
            return None
        return value

    def _cache_set(self, key: tuple[Any, ...], value: Any) -> None:
        self._cache[key] = (time.monotonic(), value)

    def _cache_invalidate(self, table_id: str) -> None:
        to_delete = [k for k in self._cache if k and k[0] == table_id]
        for k in to_delete:
            del self._cache[k]

    def __enter__(self) -> "NoCODBClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self._client.close()


# ── Factory ──────────────────────────────────────────────────────
def build_nocodb_client(settings: Any) -> NoCODBClient:
    """
    Construit un NoCODBClient depuis les settings de l'application.

    Dans settings.py, ajoutez :
        nocodb_url: str = Field(default="", env="NOCODB_URL")
        nocodb_token: str = Field(default="", env="NOCODB_TOKEN")

    Usage dans main.py (remplace build_baserow_client) :
        from src.services.nocodb_client import build_nocodb_client
        client = build_nocodb_client(get_settings())
    """
    if not settings.nocodb_url or not settings.nocodb_token:
        raise NoCODBError(
            "NOCODB_URL et NOCODB_TOKEN doivent être définis dans .env"
        )
    return NoCODBClient(
        NoCODBConfig(
            base_url=settings.nocodb_url,
            token=settings.nocodb_token,
        )
    )
