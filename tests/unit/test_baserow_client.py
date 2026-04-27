"""Tests for the Baserow client wrapper."""

from __future__ import annotations

import httpx
import pytest

from src.services.baserow_client import BaserowClient, BaserowConfig, BaserowError


def _client_with_handler(handler: httpx.MockTransport) -> BaserowClient:
    config = BaserowConfig(base_url="https://baserow.test", token="dummy")
    httpx_client = httpx.Client(
        base_url=config.base_url,
        headers=config.headers,
        transport=handler,
    )
    return BaserowClient(config, client=httpx_client)


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
