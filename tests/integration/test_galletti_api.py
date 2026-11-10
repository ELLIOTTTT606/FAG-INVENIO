"""Tests d'intégration des endpoints /galletti."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_galletti_status_reports_not_configured() -> None:
    resp = client.get("/galletti/status")
    assert resp.status_code == 200
    body = resp.json()
    assert "configured" in body
    assert body["configured"] is False  # pas de GALLETTI_COOKIE en test


def test_galletti_projects_without_cookie_returns_503() -> None:
    resp = client.get("/galletti/projects")
    assert resp.status_code == 503
    assert "GALLETTI_COOKIE" in resp.json()["detail"]


def test_galletti_project_detail_without_cookie_returns_503() -> None:
    resp = client.get("/galletti/projects/306090")
    assert resp.status_code == 503
