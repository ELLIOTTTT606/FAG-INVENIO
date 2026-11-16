"""Tests for the referential snapshot comparison ("Actualiser")."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from src.services.options_catalog import MockOptionsCatalog
from src.services.referential import diff_snapshots, take_snapshot
from tools.referential_diff import main


def _option(code: str, **fields: object) -> dict[str, object]:
    base: dict[str, object] = {
        "model": "PLP",
        "type": "HS",
        "size": "052",
        "code": code,
        "category": "Pompe eau cote utilisateur",
        "label": f"Option {code}",
        "price_eur": 100.0,
        "available": True,
    }
    base.update(fields)
    return base


def test_identical_snapshots_have_no_difference() -> None:
    options = [_option("1"), _option("2")]
    diff = diff_snapshots(options, [dict(o) for o in options])
    assert diff.is_empty
    assert diff.summary() == "Référentiel à jour : aucune différence."


def test_additions_modifications_and_removals() -> None:
    old = [_option("1"), _option("2"), _option("3")]
    new = [_option("1"), _option("2", price_eur=120.0, label="Option 2 bis"), _option("4")]
    diff = diff_snapshots(old, new)
    assert [o["code"] for o in diff.added] == ["4"]
    assert [o["code"] for o in diff.removed] == ["3"]
    assert len(diff.changed) == 1
    change = diff.changed[0]
    assert change.key == ("PLP", "HS", "052", "2")
    assert {c.field for c in change.changes} == {"price_eur", "label"}
    assert diff.summary() == "1 ajout(s), 1 modification(s), 1 suppression(s)."


def test_cosmetic_differences_are_ignored() -> None:
    old = [_option("1", label="Pompe  simple ", price_eur=100.0, tips=None)]
    new = [_option("1", label="Pompe simple", price_eur=100.001, tips="")]
    assert diff_snapshots(old, new).is_empty


def test_same_code_on_two_machines_is_two_options() -> None:
    old = [_option("1"), _option("1", size="062")]
    new = [_option("1")]
    diff = diff_snapshots(old, new)
    assert [(o["size"], o["code"]) for o in diff.removed] == [("062", "1")]


def test_markdown_report_groups_by_machine() -> None:
    diff = diff_snapshots([_option("1")], [_option("1", price_eur=150.0), _option("9", size="062")])
    report = diff.to_markdown()
    assert "## PLP HS 052" in report
    assert "**Modification** `1` Option 1 (prix : 100.0 → 150.0)" in report
    assert "## PLP HS 062" in report and "**Ajout** `9`" in report


def test_take_snapshot_reads_every_machine() -> None:
    snapshot = take_snapshot(
        MockOptionsCatalog(),
        [("PLP", "HS", "052"), ("PLP", "CS", "052")],
        taken_at=datetime(2026, 11, 16, tzinfo=UTC),
    )
    assert snapshot["taken_at"] == "2026-11-16T00:00:00+00:00"
    machines = {(o["model"], o["type"], o["size"]) for o in snapshot["options"]}
    assert machines == {("PLP", "HS", "052"), ("PLP", "CS", "052")}
    assert diff_snapshots(snapshot["options"], snapshot["options"]).is_empty


def test_cli_writes_a_report_and_flags_changes(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    old, new, report = tmp_path / "old.json", tmp_path / "new.json", tmp_path / "rapport.md"
    old.write_text(json.dumps({"options": [_option("1")]}), "utf-8")
    new.write_text(json.dumps([_option("1"), _option("2")]), "utf-8")
    assert main([str(old), str(new), "--markdown", str(report), "--fail-on-change"]) == 1
    assert "1 ajout(s)" in capsys.readouterr().out
    assert "**Ajout** `2`" in report.read_text("utf-8")
    assert main([str(old), str(old), "--fail-on-change"]) == 0
