"""Integration tests: upload DOCX/PDF through the FastAPI endpoints."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from tests.fixtures.galletti_docx import build_pac_document
from tests.fixtures.galletti_pdf import write_pac as write_pac_pdf


@pytest.fixture()
def sample_docx_bytes() -> bytes:
    document = build_pac_document()
    buf = BytesIO()
    document.save(buf)
    return buf.getvalue()


@pytest.fixture()
def sample_pdf_bytes(tmp_path: Path) -> bytes:
    pdf_path = write_pac_pdf(tmp_path / "sample.pdf")
    return pdf_path.read_bytes()


def test_health_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_parse_docx_endpoint_returns_canonical_payload(sample_docx_bytes: bytes) -> None:
    client = TestClient(app)
    files = {
        "file": (
            "sample.docx",
            sample_docx_bytes,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }
    response = client.post("/parse/docx", files=files)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["data"]["model"] == "PLP"
    assert body["data"]["family"] == "PAC"
    assert body["data"]["performance"]["cooling"]["power_kW"] == 41.7


def test_parse_pdf_endpoint_returns_canonical_payload(sample_pdf_bytes: bytes) -> None:
    client = TestClient(app)
    files = {"file": ("sample.pdf", sample_pdf_bytes, "application/pdf")}
    response = client.post("/parse/pdf", files=files)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["data"]["family"] == "PAC"
    assert body["data"]["performance"]["cooling"]["seer"] == 4.15
    assert body["data"]["performance"]["heating"]["scop"] == 4.35


def test_parse_docx_endpoint_rejects_wrong_extension() -> None:
    client = TestClient(app)
    files = {"file": ("bad.txt", b"hello", "text/plain")}
    response = client.post("/parse/docx", files=files)
    assert response.status_code == 415


def test_parse_pdf_endpoint_rejects_docx() -> None:
    client = TestClient(app)
    files = {"file": ("bad.docx", b"hello", "application/octet-stream")}
    response = client.post("/parse/pdf", files=files)
    assert response.status_code == 415


def test_parse_real_sample_file_if_present() -> None:
    sample = Path("examples/sample_galletti.docx")
    if not sample.exists():
        pytest.skip("examples/sample_galletti.docx not provided yet")
    client = TestClient(app)
    with sample.open("rb") as f:
        response = client.post(
            "/parse/docx",
            files={"file": (sample.name, f.read(), "application/octet-stream")},
        )
    assert response.status_code == 200
