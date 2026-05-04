"""Tests for tools.parser_bench against synthetic corpora."""

from __future__ import annotations

from pathlib import Path

import pytest
from docx import Document

from tests.fixtures.galletti_docx import write_geg, write_pac
from tests.fixtures.galletti_pdf import write_pac as write_pac_pdf
from tools import parser_bench


def _write_broken_docx(path: Path) -> None:
    """A DOCX with no designation and a single irrelevant paragraph."""

    document = Document()
    document.add_paragraph("Pas de fiche ici.")
    document.save(str(path))


@pytest.fixture()
def corpus(tmp_path: Path) -> Path:
    write_pac(tmp_path / "pac.docx")
    write_geg(tmp_path / "geg.docx")
    write_pac_pdf(tmp_path / "pac.pdf")
    _write_broken_docx(tmp_path / "broken.docx")
    return tmp_path


def test_bench_corpus_walks_supported_extensions_only(corpus: Path) -> None:
    (corpus / "ignored.txt").write_text("not a fiche", encoding="utf-8")
    report = parser_bench.bench_corpus(corpus)
    assert report.total == 4  # pac.docx, geg.docx, pac.pdf, broken.docx
    paths = {Path(f.path).name for f in report.fiches}
    assert "ignored.txt" not in paths


def test_bench_aggregates_family_distribution(corpus: Path) -> None:
    report = parser_bench.bench_corpus(corpus)
    # Two PAC fixtures (docx + pdf) + one GEG + the broken file
    # (which infers PAC by default since type starts with H).
    assert report.family_distribution.get("PAC", 0) >= 2
    assert report.family_distribution.get("GEG", 0) == 1


def test_bench_records_designation_found_count(corpus: Path) -> None:
    report = parser_bench.bench_corpus(corpus)
    # The broken fixture has no designation, the three others do.
    assert report.designation_found_count == 3


def test_bench_top_warnings_includes_designation_not_found(corpus: Path) -> None:
    report = parser_bench.bench_corpus(corpus)
    codes = {code for code, _ in report.warnings_top}
    assert "designation_not_found" in codes


def test_bench_field_coverage_pac_perf_is_high(corpus: Path) -> None:
    report = parser_bench.bench_corpus(corpus)
    cooling = report.field_coverage.get("performance.cooling", {})
    assert cooling.get("power_kW", 0) >= 0.5  # PAC + GEG fixtures populate it
    assert cooling.get("eer", 0) >= 0.5


def test_bench_schema_valid_for_well_formed_fiches(corpus: Path) -> None:
    report = parser_bench.bench_corpus(corpus)
    assert report.schema_valid_count >= 3


def test_bench_records_parse_error_on_unreadable_file(tmp_path: Path) -> None:
    bad = tmp_path / "corrupt.docx"
    bad.write_bytes(b"not a real docx")
    report = parser_bench.bench_corpus(tmp_path)
    assert report.total == 1
    assert report.failed == 1
    assert report.fiches[0].parse_error
    assert report.ok is False


def test_bench_to_dict_round_trip(corpus: Path) -> None:
    report = parser_bench.bench_corpus(corpus)
    payload = report.to_dict()
    assert payload["total"] == 4
    assert payload["ok"] is True
    assert isinstance(payload["fiches"], list)
    assert "field_coverage" in payload


def test_percentile_helper() -> None:
    assert parser_bench._percentile([], 0.5) == 0.0
    assert parser_bench._percentile([5.0], 0.95) == 5.0
    assert parser_bench._percentile([1.0, 2.0, 3.0, 4.0], 0.5) == 2.5
    assert parser_bench._percentile([1.0, 2.0, 3.0, 4.0], 0.95) == pytest.approx(3.85)
