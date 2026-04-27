"""Validate and normalize the options/accessoires CSV master file.

CLI:
    python -m tools.validate_csv \\
        --input examples/options_accessoires_sample.csv \\
        --schema src/schema/options_schema.json \\
        --out-valid validated/options_accessoires_sample.valid.csv \\
        --out-report reports/options_accessoires_sample.report.json

Exit code: 0 if no errors (warnings allowed), 1 otherwise.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

REQUIRED_COLUMNS: tuple[str, ...] = (
    "model",
    "family",
    "type",
    "size",
    "option_code",
    "option_category",
    "label_fr",
    "description_fr",
    "tips_fr",
    "price_eur",
    "available",
    "source_file",
    "last_updated",
)

UNIQUE_KEY: tuple[str, ...] = ("model", "size", "option_code")

TRUE_VALUES = {"true", "1", "yes", "y", "oui", "vrai"}
FALSE_VALUES = {"false", "0", "no", "n", "non", "faux", ""}


@dataclass
class Issue:
    """Single problem detected on a row or on the whole file."""

    severity: str  # "error" | "warning"
    code: str
    message: str
    row: int | None = None  # 1-based row number in the source CSV (excluding header)
    field: str | None = None


@dataclass
class Report:
    input_file: str
    schema_file: str
    total_rows: int = 0
    valid_rows: int = 0
    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)

    def add(self, issue: Issue) -> None:
        if issue.severity == "error":
            self.errors.append(issue)
        else:
            self.warnings.append(issue)

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_file": self.input_file,
            "schema_file": self.schema_file,
            "total_rows": self.total_rows,
            "valid_rows": self.valid_rows,
            "ok": self.ok,
            "errors": [asdict(i) for i in self.errors],
            "warnings": [asdict(i) for i in self.warnings],
        }


def load_schema(schema_path: Path) -> dict[str, Any]:
    with schema_path.open(encoding="utf-8") as f:
        schema: dict[str, Any] = json.load(f)
    return schema


def normalize_row(raw: dict[str, str]) -> tuple[dict[str, Any], list[Issue]]:
    """Trim, coerce types, and uppercase identifiers. Return (clean, issues)."""

    issues: list[Issue] = []
    clean: dict[str, Any] = {}

    for key, value in raw.items():
        clean[key] = (value or "").strip()

    for upper_field in ("model", "family", "type", "size", "option_code"):
        if upper_field in clean and clean[upper_field]:
            clean[upper_field] = clean[upper_field].upper()

    available_raw = str(clean.get("available", "")).lower()
    if available_raw in TRUE_VALUES:
        clean["available"] = True
    elif available_raw in FALSE_VALUES:
        clean["available"] = False
    else:
        issues.append(
            Issue(
                severity="error",
                code="invalid_boolean",
                message=f"`available` must be a boolean (got {clean.get('available')!r}).",
                field="available",
            )
        )

    price_raw = str(clean.get("price_eur", "")).replace(",", ".").strip()
    if price_raw == "":
        clean["price_eur"] = None
    else:
        try:
            clean["price_eur"] = float(price_raw)
        except ValueError:
            issues.append(
                Issue(
                    severity="error",
                    code="invalid_number",
                    message=f"`price_eur` is not a valid number (got {price_raw!r}).",
                    field="price_eur",
                )
            )
            clean["price_eur"] = None

    for text_field in ("description_fr", "tips_fr", "label_fr"):
        text = clean.get(text_field, "")
        if "\n" in text or "\r" in text:
            issues.append(
                Issue(
                    severity="warning",
                    code="multiline_value",
                    message=f"`{text_field}` contains line breaks; collapsed to spaces.",
                    field=text_field,
                )
            )
            clean[text_field] = " ".join(text.split())

    return clean, issues


def validate_rows(
    rows: Iterable[dict[str, str]],
    validator: Draft202012Validator,
) -> tuple[list[dict[str, Any]], Report, list[dict[str, str]]]:
    """Validate every row. Return (clean_rows, report, raw_rows_kept)."""

    report = Report(input_file="", schema_file="")
    clean_rows: list[dict[str, Any]] = []
    raw_kept: list[dict[str, str]] = []
    seen_keys: dict[tuple[str, ...], int] = {}

    for index, raw in enumerate(rows, start=1):
        report.total_rows += 1

        missing = [c for c in REQUIRED_COLUMNS if c not in raw]
        if missing:
            report.add(
                Issue(
                    severity="error",
                    code="missing_columns",
                    message=f"Missing columns on row: {', '.join(missing)}.",
                    row=index,
                )
            )
            continue

        clean, norm_issues = normalize_row(raw)
        for issue in norm_issues:
            issue.row = index
            report.add(issue)

        schema_errors = list(validator.iter_errors(clean))
        for err in schema_errors:
            field_name = ".".join(str(p) for p in err.absolute_path) or None
            report.add(
                Issue(
                    severity="error",
                    code="schema_violation",
                    message=err.message,
                    row=index,
                    field=field_name,
                )
            )

        key = tuple(str(clean.get(k, "")) for k in UNIQUE_KEY)
        if key in seen_keys:
            report.add(
                Issue(
                    severity="error",
                    code="duplicate_key",
                    message=(
                        f"Duplicate key {dict(zip(UNIQUE_KEY, key, strict=True))} "
                        f"already seen on row {seen_keys[key]}."
                    ),
                    row=index,
                )
            )
        else:
            seen_keys[key] = index

        if not schema_errors and not any(i.severity == "error" for i in norm_issues):
            report.valid_rows += 1
            clean_rows.append(clean)
            raw_kept.append(raw)

    return clean_rows, report, raw_kept


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(REQUIRED_COLUMNS))
        writer.writeheader()
        for row in rows:
            serialized = {
                k: ("" if row.get(k) is None else str(row.get(k))) for k in REQUIRED_COLUMNS
            }
            writer.writerow(serialized)


def write_report(path: Path, report: Report) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)


def run(
    input_path: Path,
    schema_path: Path,
    out_valid: Path | None,
    out_report: Path | None,
) -> Report:
    schema = load_schema(schema_path)
    validator = Draft202012Validator(schema)

    with input_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            report = Report(input_file=str(input_path), schema_file=str(schema_path))
            report.add(
                Issue(severity="error", code="empty_file", message="CSV has no header row.")
            )
            return report

        header_missing = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
        report = Report(input_file=str(input_path), schema_file=str(schema_path))
        if header_missing:
            report.add(
                Issue(
                    severity="error",
                    code="missing_header_columns",
                    message=f"Header is missing required columns: {', '.join(header_missing)}",
                )
            )

        clean_rows, row_report, _ = validate_rows(reader, validator)
        report.total_rows = row_report.total_rows
        report.valid_rows = row_report.valid_rows
        report.errors.extend(row_report.errors)
        report.warnings.extend(row_report.warnings)

    if out_valid is not None and report.ok:
        write_csv(out_valid, clean_rows)

    if out_report is not None:
        write_report(out_report, report)

    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="validate-options-csv",
        description="Validate and normalize an INVENIO options/accessoires CSV.",
    )
    parser.add_argument("--input", required=True, type=Path, help="Input CSV path.")
    parser.add_argument(
        "--schema",
        required=False,
        type=Path,
        default=Path("src/schema/options_schema.json"),
        help="JSON Schema for an options row.",
    )
    parser.add_argument(
        "--out-valid",
        type=Path,
        default=None,
        help="If set and the file is valid, write a normalized CSV here.",
    )
    parser.add_argument(
        "--out-report",
        type=Path,
        default=None,
        help="Write a JSON report (errors + warnings) here.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    report = run(args.input, args.schema, args.out_valid, args.out_report)

    print(
        f"rows={report.total_rows} valid={report.valid_rows} "
        f"errors={len(report.errors)} warnings={len(report.warnings)}"
    )
    for issue in report.errors[:20]:
        loc = f"row {issue.row}" if issue.row else "file"
        field_part = f" [{issue.field}]" if issue.field else ""
        print(f"  ERROR {loc}{field_part}: {issue.code} - {issue.message}")
    for issue in report.warnings[:20]:
        loc = f"row {issue.row}" if issue.row else "file"
        field_part = f" [{issue.field}]" if issue.field else ""
        print(f"  WARN  {loc}{field_part}: {issue.code} - {issue.message}")

    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
