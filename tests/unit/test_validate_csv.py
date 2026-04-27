"""Tests for tools.validate_csv."""

from __future__ import annotations

from pathlib import Path

from tools.validate_csv import REQUIRED_COLUMNS, normalize_row, run

SCHEMA_PATH = Path("src/schema/options_schema.json")


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    columns = list(REQUIRED_COLUMNS)
    lines = [",".join(columns)]
    for row in rows:
        lines.append(",".join(row.get(c, "") for c in columns))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _valid_row(**overrides: str) -> dict[str, str]:
    base = {
        "model": "MPET18-C",
        "family": "C",
        "type": "HS",
        "size": "18",
        "option_code": "1",
        "option_category": "Pompe eau",
        "label_fr": "Pompe simple",
        "description_fr": "Pompe simple non modulante",
        "tips_fr": "Verifier raccordement",
        "price_eur": "",
        "available": "true",
        "source_file": "source1.docx",
        "last_updated": "2026-04-27",
    }
    base.update(overrides)
    return base


def test_normalize_row_uppercases_identifiers_and_coerces_boolean() -> None:
    raw = _valid_row(model="mpet18-c", available="oui")
    clean, issues = normalize_row(raw)
    assert clean["model"] == "MPET18-C"
    assert clean["available"] is True
    assert clean["price_eur"] is None
    assert not [i for i in issues if i.severity == "error"]


def test_normalize_row_flags_invalid_boolean() -> None:
    raw = _valid_row(available="maybe")
    _, issues = normalize_row(raw)
    assert any(i.code == "invalid_boolean" for i in issues)


def test_normalize_row_collapses_multiline_descriptions() -> None:
    raw = _valid_row(description_fr="Ligne 1\nLigne 2")
    clean, issues = normalize_row(raw)
    assert "\n" not in clean["description_fr"]
    assert any(i.code == "multiline_value" for i in issues)


def test_normalize_row_parses_french_decimal() -> None:
    raw = _valid_row(price_eur="1234,50")
    clean, _ = normalize_row(raw)
    assert clean["price_eur"] == 1234.5


def test_run_happy_path(tmp_path: Path) -> None:
    csv_path = tmp_path / "valid.csv"
    _write_csv(csv_path, [_valid_row(option_code="0"), _valid_row(option_code="1")])
    out_valid = tmp_path / "valid.out.csv"
    out_report = tmp_path / "valid.report.json"

    report = run(csv_path, SCHEMA_PATH, out_valid, out_report)

    assert report.ok is True
    assert report.total_rows == 2
    assert report.valid_rows == 2
    assert out_valid.exists()
    assert out_report.exists()


def test_run_detects_duplicate_key(tmp_path: Path) -> None:
    csv_path = tmp_path / "dup.csv"
    _write_csv(csv_path, [_valid_row(), _valid_row()])

    report = run(csv_path, SCHEMA_PATH, None, None)

    assert report.ok is False
    assert any(i.code == "duplicate_key" for i in report.errors)


def test_run_detects_schema_violation(tmp_path: Path) -> None:
    csv_path = tmp_path / "bad.csv"
    _write_csv(csv_path, [_valid_row(family="X")])

    report = run(csv_path, SCHEMA_PATH, None, None)

    assert report.ok is False
    assert any(i.code == "schema_violation" for i in report.errors)


def test_run_detects_missing_header_column(tmp_path: Path) -> None:
    csv_path = tmp_path / "missing.csv"
    columns = [c for c in REQUIRED_COLUMNS if c != "tips_fr"]
    csv_path.write_text(",".join(columns) + "\n", encoding="utf-8")

    report = run(csv_path, SCHEMA_PATH, None, None)

    assert report.ok is False
    assert any(i.code == "missing_header_columns" for i in report.errors)


def test_sample_csv_validates(tmp_path: Path) -> None:
    sample = Path("examples/options_accessoires_sample.csv")
    report = run(sample, SCHEMA_PATH, None, tmp_path / "report.json")
    assert report.ok is True, report.errors
