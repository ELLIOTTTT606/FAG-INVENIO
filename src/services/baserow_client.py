"""Minimal Baserow REST client.

Tables documented in `docs/architecture.md`. Authentication uses a database
token in the `Authorization: Token <token>` header.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


class BaserowError(RuntimeError):
    """Raised when the Baserow API returns an error response."""


@dataclass(frozen=True)
class BaserowConfig:
    base_url: str
    token: str
    timeout_seconds: float = 10.0

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json",
        }


class BaserowClient:
    """Thin wrapper. Use one instance per process.

    Use as a context manager so the underlying httpx client is closed.
    """

    def __init__(self, config: BaserowConfig, *, client: httpx.Client | None = None) -> None:
        self._config = config
        self._client = client or httpx.Client(
            base_url=config.base_url.rstrip("/"),
            headers=config.headers,
            timeout=config.timeout_seconds,
        )

    def __enter__(self) -> BaserowClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def list_rows(
        self,
        table_id: int,
        *,
        page: int = 1,
        size: int = 100,
        user_field_names: bool = True,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "page": page,
            "size": size,
            "user_field_names": str(user_field_names).lower(),
        }
        response = self._client.get(f"/api/database/rows/table/{table_id}/", params=params)
        return self._unwrap(response)

    def create_row(
        self,
        table_id: int,
        payload: dict[str, Any],
        *,
        user_field_names: bool = True,
    ) -> dict[str, Any]:
        params = {"user_field_names": str(user_field_names).lower()}
        response = self._client.post(
            f"/api/database/rows/table/{table_id}/",
            params=params,
            json=payload,
        )
        return self._unwrap(response)

    @staticmethod
    def _unwrap(response: httpx.Response) -> dict[str, Any]:
        if response.is_error:
            raise BaserowError(
                f"Baserow {response.request.method} {response.request.url} "
                f"returned {response.status_code}: {response.text}"
            )
        data = response.json()
        if not isinstance(data, dict):
            raise BaserowError(f"Unexpected Baserow response shape: {type(data).__name__}")
        return data
