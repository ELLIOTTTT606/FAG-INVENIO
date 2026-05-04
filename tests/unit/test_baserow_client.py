"""Tests for the Baserow client wrapper."""

from __future__ import annotations

import httpx
import pytest

from src.services.baserow_client import BaserowClient, BaserowConfig, BaserowError


def _client_with_handler(
    handler: httpx.MockTransport,
    *,
    config: BaserowConfig | None = None,
    sleep_calls: list[float] | None = None,
) -> BaserowClient:
    cfg = config or BaserowConfig(base_url="https://baserow.test", token="dummy")
    httpx_client = httpx.Client(
        base_url=cfg.base_url,
        headers=cfg.headers,
        transport=handler,
    )
    sleep = (lambda d: sleep_calls.append(d)) if sleep_calls is not None else (lambda _: None)
    return BaserowClient(cfg, client=httpx_client, sleep=sleep)


def test_list_rows_sends_token_header_and_unwraps_response() -> None:
    captured: dict[str, object] = {}

    def handle(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("Authorization")
        return httpx.Response(200, json={"count": 1, "results": [{"id": 1}]})

    with _client_with_handler(httpx.MockTransport(handle)) as client:
        data = client.list_rows(123, page=2, size=50)

    assert captured["auth"] == "Token dummy"
    assert "table/123" in str(captured["url"])
    assert data["results"][0]["id"] == 1


def test_create_row_posts_payload_and_returns_dict() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        return httpx.Response(200, json={"id": 42, "label": "Pompe"})

    with _client_with_handler(httpx.MockTransport(handle)) as client:
        data = client.create_row(7, {"label": "Pompe"})

    assert data["id"] == 42


def test_error_response_raises_baserow_error() -> None:
    def handle(_: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="forbidden")

    with _client_with_handler(httpx.MockTransport(handle)) as client, pytest.raises(BaserowError):
        client.list_rows(1)


def test_retries_on_429_then_succeeds() -> None:
    calls = {"count": 0}

    def handle(_: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] < 3:
            return httpx.Response(429, text="slow down")
        return httpx.Response(200, json={"results": [{"id": 1}], "next": None})

    sleep_calls: list[float] = []
    config = BaserowConfig(
        base_url="https://baserow.test",
        token="dummy",
        max_retries=4,
        backoff_initial_seconds=0.01,
        cache_ttl_seconds=0,
    )
    with _client_with_handler(
        httpx.MockTransport(handle), config=config, sleep_calls=sleep_calls
    ) as client:
        data = client.list_rows(1)

    assert data["results"][0]["id"] == 1
    assert calls["count"] == 3
    assert len(sleep_calls) == 2  # two retries -> two sleeps


def test_gives_up_after_max_retries_on_persistent_5xx() -> None:
    def handle(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="down")

    config = BaserowConfig(
        base_url="https://baserow.test",
        token="dummy",
        max_retries=2,
        backoff_initial_seconds=0.0,
        cache_ttl_seconds=0,
    )
    with (
        _client_with_handler(httpx.MockTransport(handle), config=config) as client,
        pytest.raises(BaserowError),
    ):
        client.list_rows(1)


def test_cache_short_circuits_repeated_reads() -> None:
    calls = {"count": 0}

    def handle(_: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(200, json={"results": [{"id": 1}], "next": None})

    config = BaserowConfig(
        base_url="https://baserow.test", token="dummy", cache_ttl_seconds=60
    )
    with _client_with_handler(httpx.MockTransport(handle), config=config) as client:
        client.list_rows(1)
        client.list_rows(1)
        client.list_rows(1)

    assert calls["count"] == 1


def test_create_row_invalidates_cache_for_table() -> None:
    counts = {"GET": 0, "POST": 0}

    def handle(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            counts["GET"] += 1
            return httpx.Response(200, json={"results": [{"id": counts["GET"]}], "next": None})
        counts["POST"] += 1
        return httpx.Response(200, json={"id": 99})

    config = BaserowConfig(
        base_url="https://baserow.test", token="dummy", cache_ttl_seconds=60
    )
    with _client_with_handler(httpx.MockTransport(handle), config=config) as client:
        client.list_rows(7)  # cached
        client.create_row(7, {"label": "x"})
        client.list_rows(7)  # cache invalidated -> hits server again

    assert counts["GET"] == 2
    assert counts["POST"] == 1


def test_create_rows_batch_posts_items_and_returns_created_payloads() -> None:
    captured: dict[str, object] = {}

    def handle(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        captured["body"] = request.read()
        return httpx.Response(
            200,
            json={"items": [{"id": 1, "label": "a"}, {"id": 2, "label": "b"}]},
        )

    config = BaserowConfig(
        base_url="https://baserow.test", token="dummy", cache_ttl_seconds=0
    )
    with _client_with_handler(httpx.MockTransport(handle), config=config) as client:
        out = client.create_rows(7, [{"label": "a"}, {"label": "b"}])

    assert captured["method"] == "POST"
    assert "/table/7/batch/" in str(captured["url"])
    assert b'"items"' in captured["body"]  # type: ignore[arg-type]
    assert [row["id"] for row in out] == [1, 2]


def test_create_rows_short_circuits_on_empty_payload() -> None:
    def handle(_: httpx.Request) -> httpx.Response:
        raise AssertionError("should not call Baserow with an empty batch")

    with _client_with_handler(httpx.MockTransport(handle)) as client:
        assert client.create_rows(7, []) == []


def test_update_row_patches_and_invalidates_cache() -> None:
    counts = {"GET": 0, "PATCH": 0}

    def handle(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            counts["GET"] += 1
            return httpx.Response(200, json={"results": [{"id": counts["GET"]}], "next": None})
        counts["PATCH"] += 1
        return httpx.Response(200, json={"id": 99, "label": "patched"})

    config = BaserowConfig(
        base_url="https://baserow.test", token="dummy", cache_ttl_seconds=60
    )
    with _client_with_handler(httpx.MockTransport(handle), config=config) as client:
        client.list_rows(11)  # warms the cache
        result = client.update_row(11, 99, {"label": "patched"})
        client.list_rows(11)  # should hit the server again

    assert result["label"] == "patched"
    assert counts["PATCH"] == 1
    assert counts["GET"] == 2  # cache invalidated by the PATCH


def test_create_rows_raises_on_unexpected_response_shape() -> None:
    def handle(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"oops": True})

    with _client_with_handler(httpx.MockTransport(handle)) as client, pytest.raises(BaserowError):
        client.create_rows(7, [{"label": "a"}])


def test_ping_returns_false_on_error() -> None:
    def handle(_: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="nope")

    config = BaserowConfig(
        base_url="https://baserow.test",
        token="dummy",
        max_retries=0,
        cache_ttl_seconds=0,
    )
    with _client_with_handler(httpx.MockTransport(handle), config=config) as client:
        assert client.ping() is False
