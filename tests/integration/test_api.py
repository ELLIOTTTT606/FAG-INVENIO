"""Integration tests: upload DOCX/PDF through the FastAPI endpoints."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.main import app, get_contacts_repository, get_options_catalog
from src.services.contacts_repo import MockContactsRepository
from src.services.options_catalog import MockOptionsCatalog
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
def mock_catalog() -> MockOptionsCatalog:
    catalog = MockOptionsCatalog()
    get_options_catalog.cache_clear()
    app.dependency_overrides[get_options_catalog] = lambda: catalog
    yield catalog
    app.dependency_overrides.pop(get_options_catalog, None)


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


def test_create_client_returns_201_and_persists_record(
    mock_repo: MockContactsRepository,
) -> None:
    client = TestClient(app)
    payload = {
        "client_code": "c-test",
        "client_name": "Test Co",
        "postal_code": "75015",
        "department": "75",
    }
    response = client.post("/clients", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["client_code"] == "C-TEST"
    assert body["client_name"] == "Test Co"
    # Lookup confirms persistence in the mock store.
    assert any(c.client_code == "C-TEST" for c in mock_repo.search_clients("test"))


def test_create_client_returns_409_on_duplicate(mock_repo: MockContactsRepository) -> None:
    _ = mock_repo
    client = TestClient(app)
    payload = {
        "client_code": "C-DUP",
        "client_name": "First",
        "postal_code": "75015",
        "department": "75",
    }
    assert client.post("/clients", json=payload).status_code == 201
    response = client.post("/clients", json={**payload, "client_name": "Second"})
    assert response.status_code == 409


def test_update_client_returns_200_and_persists(
    mock_repo: MockContactsRepository,
) -> None:
    client = TestClient(app)
    created = client.post(
        "/clients",
        json={
            "client_code": "C-EDIT",
            "client_name": "Old name",
            "postal_code": "75015",
            "department": "75",
        },
    ).json()
    response = client.patch(
        f"/clients/{created['id']}",
        json={
            "client_code": "C-EDIT",
            "client_name": "New name",
            "postal_code": "75015",
            "department": "75",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    assert body["client_name"] == "New name"
    [matched] = mock_repo.search_clients("new name")
    assert matched.client_name == "New name"


def test_update_client_returns_404_when_id_missing(mock_repo: MockContactsRepository) -> None:
    _ = mock_repo
    client = TestClient(app)
    response = client.patch(
        "/clients/999999",
        json={
            "client_code": "X",
            "client_name": "X",
            "postal_code": "75015",
            "department": "75",
        },
    )
    assert response.status_code == 404


def test_update_client_returns_409_on_duplicate_code(mock_repo: MockContactsRepository) -> None:
    client = TestClient(app)
    a = client.post(
        "/clients",
        json={
            "client_code": "C-A",
            "client_name": "A",
            "postal_code": "75015",
            "department": "75",
        },
    ).json()
    client.post(
        "/clients",
        json={
            "client_code": "C-B",
            "client_name": "B",
            "postal_code": "75015",
            "department": "75",
        },
    )
    _ = mock_repo  # populated through the API above
    response = client.patch(
        f"/clients/{a['id']}",
        json={
            "client_code": "C-B",  # collides with the second client
            "client_name": "A renamed",
            "postal_code": "75015",
            "department": "75",
        },
    )
    assert response.status_code == 409


def test_create_client_validates_postal_and_department(
    mock_repo: MockContactsRepository,
) -> None:
    _ = mock_repo
    client = TestClient(app)
    response = client.post(
        "/clients",
        json={
            "client_code": "C1",
            "client_name": "X",
            "postal_code": "abc",
            "department": "75",
        },
    )
    assert response.status_code == 422
    response = client.post(
        "/clients",
        json={
            "client_code": "C1",
            "client_name": "X",
            "postal_code": "75001",
            "department": "FOO",
        },
    )
    assert response.status_code == 422


def test_options_endpoint_returns_pac_catalog(mock_catalog: MockOptionsCatalog) -> None:
    _ = mock_catalog
    client = TestClient(app)
    response = client.get("/options", params={"model": "PLP", "type": "HS", "size": "052"})
    assert response.status_code == 200
    body = response.json()
    assert body["model"] == "PLP" and body["type"] == "HS" and body["size"] == "052"
    codes = {row["code"] for row in body["options"]}
    assert {"0", "1", "P", "C", "L"}.issubset(codes)
    categories = {row["category"] for row in body["options"]}
    assert "Kit antigel" in categories  # PAC-only


def test_options_endpoint_returns_geg_catalog(mock_catalog: MockOptionsCatalog) -> None:
    _ = mock_catalog
    client = TestClient(app)
    response = client.get("/options", params={"model": "VLS", "type": "CS", "size": "202"})
    assert response.status_code == 200
    body = response.json()
    categories = {row["category"] for row in body["options"]}
    assert "Recuperation de chaleur" in categories
    assert "Kit antigel" not in categories


def test_baserow_status_endpoint_reports_mock_when_unconfigured() -> None:
    client = TestClient(app)
    response = client.get("/admin/baserow-status")
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] in {"mock", "live"}
    assert "tables" in body and isinstance(body["tables"], dict)


def test_options_endpoint_requires_all_query_params() -> None:
    client = TestClient(app)
    response = client.get("/options", params={"model": "PLP", "type": "HS"})
    assert response.status_code == 422  # missing 'size'


def _generation_payload() -> dict:
    return {
        "record": {
            "family": "PAC",
            "model": "PLP",
            "size": "052",
            "type": "HS",
            "designation_code": "PLP052HS2B A000CE000I00110 0000000I000000000000",
            "designation_blocks": None,
            "conditions": {"cooling": {"water_in_C": 12.0}, "heating": {"water_in_C": 40.0}},
            "performance": {"cooling": {"power_kW": 41.7}, "heating": {"power_kW": 52.3}},
            "general": {"refrigerant": "R290"},
            "options": [
                {
                    "code": "P",
                    "category": "Kit antigel",
                    "label": "Protection echangeur",
                    "selected": True,
                    "decoded": True,
                }
            ],
            "warnings": [],
            "acoustic": {},
            "norm": {},
            "hydraulics": {},
        },
        "contacts": {
            "department": "69",
            "tci": {"name": "Camille", "email": "c@x.com", "phone": "0472001234"},
            "tcs": None,
            "solution": None,
        },
        "selected_option_codes": ["P"],
        "document_reference": "INV-DEMO",
    }


def test_generate_preview_returns_html_with_selected_options() -> None:
    client = TestClient(app)
    response = client.post("/generate/preview", json=_generation_payload())
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    body = response.text
    assert "PLP" in body and "052" in body
    assert "Protection echangeur" in body
    assert "INV-DEMO" in body


def test_generate_pdf_returns_pdf_bytes_and_filename_header() -> None:
    client = TestClient(app)
    response = client.post("/generate/pdf", json=_generation_payload())
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "INVENIO-plp-052-hs.pdf" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF-")


_TINY_PNG_DATA_URL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgAAIA"
    "AAUAAarVyFEAAAAASUVORK5CYII="
)


def test_generate_preview_renders_plans_section() -> None:
    payload = _generation_payload()
    payload["plans"] = [{"name": "Vue de face", "data_url": _TINY_PNG_DATA_URL}]
    client = TestClient(app)
    response = client.post("/generate/preview", json=payload)
    assert response.status_code == 200
    body = response.text
    assert 'id="plans"' in body
    assert "Vue de face" in body
    assert 'href="#plans"' in body


def test_generate_pdf_with_plans() -> None:
    payload = _generation_payload()
    payload["plans"] = [
        {"name": "Plan 1", "data_url": _TINY_PNG_DATA_URL},
        {"name": "Plan 2", "data_url": _TINY_PNG_DATA_URL},
    ]
    client = TestClient(app)
    response = client.post("/generate/pdf", json=payload)
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-")


def test_generate_rejects_invalid_data_url() -> None:
    payload = _generation_payload()
    payload["plans"] = [
        {
            "name": "Pas un plan",
            # Same length as _TINY_PNG_DATA_URL so pydantic min_length passes,
            # but the MIME type is rejected by _validate_plans (text/plain).
            "data_url": "data:text/plain;base64," + "A" * 100,
        }
    ]
    client = TestClient(app)
    response = client.post("/generate/preview", json=payload)
    assert response.status_code == 400


def test_generate_rejects_too_many_plans() -> None:
    payload = _generation_payload()
    payload["plans"] = [
        {"name": f"Plan {i}", "data_url": _TINY_PNG_DATA_URL} for i in range(6)
    ]
    client = TestClient(app)
    response = client.post("/generate/preview", json=payload)
    assert response.status_code == 422  # pydantic max_length validation


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
