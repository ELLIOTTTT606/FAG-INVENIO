"""Minimal Baserow REST client with retries + TTL cache.

Tables documented in `docs/architecture.md`. Authentication uses a database
token in the `Authorization: Token <token>` header.

Retries: 429 / 5xx responses are retried up to `max_retries` times with
exponential backoff (250 ms, 500 ms, 1 s, ...). Network/timeout errors
follow the same policy.

Cache: read calls (`list_rows`, `iter_all_rows`) are memoized in process
for `cache_ttl_seconds` to keep Baserow load low; mutations
(`create_row`) invalidate the per-table cache.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

import httpx


class BaserowError(RuntimeError):
    """Raised when the Baserow API returns an error response."""


@dataclass(frozen=True)
class BaserowConfig:
    base_url: str
    token: str
    timeout_seconds: float = 10.0
    max_retries: int = 3
    backoff_initial_seconds: float = 0.25
    backoff_factor: float = 2.0
    cache_ttl_seconds: int = 300

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json",
        }


@dataclass
class _CacheEntry:
    expires_at: float
    value: Any


@dataclass
class _Cache:
    """Tiny thread-safe TTL cache keyed by an arbitrary hashable."""

    ttl_seconds: int
    entries: dict[Any, _CacheEntry] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def get(self, key: Any) -> Any | None:
        if self.ttl_seconds <= 0:
            return None
        with self.lock:
            entry = self.entries.get(key)
            if entry is None:
                return None
            if entry.expires_at < time.monotonic():
                self.entries.pop(key, None)
                return None
            return entry.value

    def set(self, key: Any, value: Any) -> None:
        if self.ttl_seconds <= 0:
            return
        with self.lock:
            self.entries[key] = _CacheEntry(
                expires_at=time.monotonic() + self.ttl_seconds, value=value
            )

    def invalidate(self, predicate: Callable[[Any], bool]) -> None:
        with self.lock:
            for key in list(self.entries.keys()):
                if predicate(key):
                    self.entries.pop(key, None)

    def clear(self) -> None:
        with self.lock:
            self.entries.clear()


_RETRY_STATUS = {408, 425, 429, 500, 502, 503, 504}


class BaserowClient:
    """Thin wrapper. Use one instance per process.

    Use as a context manager so the underlying httpx client is closed.
    """

    def __init__(
        self,
        config: BaserowConfig,
        *,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._config = config
        self._client = client or httpx.Client(
            base_url=config.base_url.rstrip("/"),
            headers=config.headers,
            timeout=config.timeout_seconds,
        )
        self._sleep = sleep
        self._cache = _Cache(ttl_seconds=config.cache_ttl_seconds)

    def __enter__(self) -> BaserowClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    # -- public API ---------------------------------------------------------

    def list_rows(
        self,
        table_id: int,
        *,
        page: int = 1,
        size: int = 100,
        user_field_names: bool = True,
    ) -> dict[str, Any]:
        cache_key = ("list_rows", table_id, page, size, user_field_names)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        params: dict[str, Any] = {
            "page": page,
            "size": size,
            "user_field_names": str(user_field_names).lower(),
        }
        response = self._request_with_retries(
            "GET", f"/api/database/rows/table/{table_id}/", params=params
        )
        data = self._unwrap(response)
        self._cache.set(cache_key, data)
        return data

    def iter_all_rows(
        self,
        table_id: int,
        *,
        size: int = 200,
        user_field_names: bool = True,
    ) -> Iterator[dict[str, Any]]:
        """Yield every row of `table_id`, walking pages until exhausted."""

        page = 1
        while True:
            response = self.list_rows(
                table_id, page=page, size=size, user_field_names=user_field_names
            )
            results = response.get("results") or []
            for row in results:
                if isinstance(row, dict):
                    yield row
            if not response.get("next") or not results:
                return
            page += 1

    def create_row(
        self,
        table_id: int,
        payload: dict[str, Any],
        *,
        user_field_names: bool = True,
    ) -> dict[str, Any]:
        params = {"user_field_names": str(user_field_names).lower()}
        response = self._request_with_retries(
            "POST",
            f"/api/database/rows/table/{table_id}/",
            params=params,
            json=payload,
        )
        # Mutating writes invalidate cached lists for this table.
        self._cache.invalidate(lambda key: isinstance(key, tuple) and len(key) >= 2 and key[1] == table_id)
        return self._unwrap(response)

    def create_rows(
        self,
        table_id: int,
        payloads: list[dict[str, Any]],
        *,
        user_field_names: bool = True,
    ) -> list[dict[str, Any]]:
        """Batch-create up to ~200 rows in one Baserow call.

        Baserow caps the per-batch payload at 200 items; callers must chunk.
        """

        if not payloads:
            return []
        params = {"user_field_names": str(user_field_names).lower()}
        response = self._request_with_retries(
            "POST",
            f"/api/database/rows/table/{table_id}/batch/",
            params=params,
            json={"items": payloads},
        )
        self._cache.invalidate(
            lambda key: isinstance(key, tuple) and len(key) >= 2 and key[1] == table_id
        )
        data = self._unwrap(response)
        items = data.get("items")
        if not isinstance(items, list):
            raise BaserowError(
                f"Unexpected batch response shape: missing 'items' (got {data!r})."
            )
        return [item for item in items if isinstance(item, dict)]

    def update_row(
        self,
        table_id: int,
        row_id: int,
        payload: dict[str, Any],
        *,
        user_field_names: bool = True,
    ) -> dict[str, Any]:
        """Patch an existing row. Only fields present in `payload` are touched."""

        params = {"user_field_names": str(user_field_names).lower()}
        response = self._request_with_retries(
            "PATCH",
            f"/api/database/rows/table/{table_id}/{row_id}/",
            params=params,
            json=payload,
        )
        self._cache.invalidate(
            lambda key: isinstance(key, tuple) and len(key) >= 2 and key[1] == table_id
        )
        return self._unwrap(response)

    def ping(self) -> bool:
        """Return True if the configured token can list any database row endpoint."""

        # Hit a cheap endpoint; Baserow returns 200 + JSON for an empty table.
        try:
            response = self._request_with_retries("GET", "/api/database/tokens/check/")
        except BaserowError:
            return False
        return response.status_code < 400

    # -- internals ----------------------------------------------------------

    def _request_with_retries(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        attempts = self._config.max_retries + 1
        last_response: httpx.Response | None = None
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                response = self._client.request(method, url, **kwargs)
            except httpx.HTTPError as err:
                last_error = err
                last_response = None
            else:
                last_error = None
                last_response = response
                if response.status_code not in _RETRY_STATUS:
                    return response
            if attempt + 1 >= attempts:
                break
            backoff = self._config.backoff_initial_seconds * (
                self._config.backoff_factor ** attempt
            )
            self._sleep(min(backoff, 8.0))

        if last_response is not None:
            return last_response
        # We exhausted retries on transport errors; bubble up.
        raise BaserowError(
            f"Baserow {method} {url} failed: {last_error}"
        ) from last_error

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
