"""Integration tests: upload DOCX/PDF through the FastAPI endpoints."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.main import app, get_contacts_repository
from src.services.contacts_repo import MockContactsRepository
from tests.fixtures.galletti_docx import build_pac_document
from tests.fixtures.galletti_pdf import write_pac as write_pac_pdf


@pytest.fixture()
def mock_repo() -> MockContactsRepository:
    repo = MockContactsRepository()
    get_contacts_repository.cache_clear()
    app.dependency_overrides[get_contacts_repository] = lambda: repo
    yield repo
    app.dependency_overrides.pop(get_contacts_repository, None)


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


def test_search_clients_requires_at_least_two_characters(mock_repo: MockContactsRepository) -> None:
    _ = mock_repo
    client = TestClient(app)
    response = client.get("/clients/search", params={"q": "a"})
    assert response.status_code == 200
    assert response.json() == []


def test_search_clients_returns_matching_records(mock_repo: MockContactsRepository) -> None:
    _ = mock_repo
    client = TestClient(app)
    response = client.get("/clients/search", params={"q": "lyon"})
    assert response.status_code == 200
    body = response.json()
    assert any("Lyon" in row["client_name"] for row in body)
    assert all(set(row.keys()) >= {"client_code", "client_name", "postal_code", "department"} for row in body)


def test_contacts_endpoint_returns_full_payload_for_known_department(
    mock_repo: MockContactsRepository,
) -> None:
    _ = mock_repo
    client = TestClient(app)
    response = client.get("/contacts/department/69")
    assert response.status_code == 200
    body = response.json()
    assert body["department"] == "69"
    assert body["tci"]["name"]
    assert body["tcs"]["email"].endswith("@france-air.com")
    assert body["solution"]["phone"]


def test_contacts_endpoint_returns_solution_only_for_unknown_department(
    mock_repo: MockContactsRepository,
) -> None:
    _ = mock_repo
    client = TestClient(app)
    response = client.get("/contacts/department/88")
    body = response.json()
    assert body["department"] == "88"
    assert body["tci"] is None
    assert body["tcs"] is None
    assert body["solution"] is not None


def test_contacts_endpoint_rejects_invalid_department_format() -> None:
    client = TestClient(app)
    response = client.get("/contacts/department/foo")
    assert response.status_code == 400


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
