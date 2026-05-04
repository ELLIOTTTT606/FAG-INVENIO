"""Run the DOCX + PDF parsers across a corpus of GALLETTI fiches.

Produces a structured report on:
  - per-fiche outcome (path, format, family, model/size/type, schema
    validity, warnings, parse duration);
  - aggregate metrics (PAC/GEG distribution, success rate, top
    warnings, field coverage per canonical section, parse-time stats).

Use this to track parser quality over a real FA corpus and to spot
gaps in `src/parser/mapping.csv` that surface as low coverage on a
specific field.

CLI:
    python -m tools.parser_bench \\
        --input path/to/corpus \\
        [--output bench-report.json] \\
        [--strict-schema]

Exit codes: 0 if every fiche parsed successfully (schema valid + no
parse error); 1 if any fiche failed.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from src.parser._common import PARSER_VERSION
from src.parser.docx_parser import parse_docx
from src.parser.pdf_parser import parse_pdf

SUPPORTED_EXTENSIONS = (".docx", ".pdf")
SECTIONS_FOR_COVERAGE = (
    ("conditions.cooling", ("water_in_C", "water_out_C", "glycol_percent",
                            "air_temp_C", "air_humidity_percent", "load_percent")),
    ("conditions.heating", ("water_in_C", "water_out_C", "glycol_percent",
                            "air_temp_C", "air_humidity_percent", "load_percent")),
    ("performance.cooling", ("power_kW", "power_uni_kW", "water_flow_lph",
                             "pressure_drop_kPa", "compressors_power_kW",
                             "compressors_current_A", "total_power_kW",
                             "total_current_A", "eer", "eer_uni", "seer")),
    ("performance.heating", ("power_kW", "power_uni_kW", "water_flow_lph",
                             "pressure_drop_kPa", "compressors_power_kW",
                             "compressors_current_A", "total_power_kW",
                             "total_current_A", "cop", "cop_uni", "scop",
                             "eta_s_percent", "seasonal_class")),
    ("acoustic", ("free_field_distance_m", "directionality_factor")),
    ("norm", ("uni_en_14511_applied", "uni_en_14511_version")),
    ("general", ("max_current_A", "starting_current_A", "sound_power_lw_dBA",
                 "sound_pressure_lp_dBA", "source_air_flow_m3h",
                 "source_fans_count", "refrigerant", "gwp", "weight_kg", "supply")),
)


@dataclass
class FicheReport:
    path: str
    format: str
    parser_version: str = PARSER_VERSION
    duration_ms: float = 0.0
    parse_error: str | None = None
    schema_valid: bool = False
    schema_errors: list[str] = field(default_factory=list)
    family: str | None = None
    model: str = ""
    size: str = ""
    type: str = ""
    designation_found: bool = False
    warning_codes: list[str] = field(default_factory=list)
    field_presence: dict[str, dict[str, bool]] = field(default_factory=dict)


@dataclass
class BenchReport:
    corpus_root: str
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    schema_valid_count: int = 0
    designation_found_count: int = 0
    family_distribution: dict[str, int] = field(default_factory=dict)
    warnings_top: list[tuple[str, int]] = field(default_factory=list)
    field_coverage: dict[str, dict[str, float]] = field(default_factory=dict)
    duration_ms_stats: dict[str, float] = field(default_factory=dict)
    fiches: list[FicheReport] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.failed == 0 and self.total > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            **{k: v for k, v in asdict(self).items() if k != "fiches"},
            "ok": self.ok,
            "fiches": [asdict(f) for f in self.fiches],
        }


def _walk_corpus(root: Path) -> list[Path]:
    if root.is_file() and root.suffix.lower() in SUPPORTED_EXTENSIONS:
        return [root]
    return sorted(
        p
        for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def _has_value(value: Any) -> bool:
    if value is None or value == "":
        return False
    if isinstance(value, dict):
        return any(_has_value(v) for v in value.values())
    if isinstance(value, list):
        return any(_has_value(v) for v in value)
    return True


def _resolve(record: dict[str, Any], dotted_path: str) -> Any:
    cursor: Any = record
    for part in dotted_path.split("."):
        if not isinstance(cursor, dict):
            return None
        cursor = cursor.get(part)
    return cursor


def _field_presence(record: dict[str, Any]) -> dict[str, dict[str, bool]]:
    result: dict[str, dict[str, bool]] = {}
    for section, fields in SECTIONS_FOR_COVERAGE:
        section_node = _resolve(record, section)
        per_field: dict[str, bool] = {}
        for fname in fields:
            value = section_node.get(fname) if isinstance(section_node, dict) else None
            per_field[fname] = _has_value(value)
        result[section] = per_field
    return result


def _bench_one(path: Path, validator: Draft202012Validator) -> FicheReport:
    fmt = "docx" if path.suffix.lower() == ".docx" else "pdf"
    report = FicheReport(path=str(path), format=fmt)
    started = time.perf_counter()
    try:
        result = parse_docx(path) if fmt == "docx" else parse_pdf(path)
    except Exception as err:  # noqa: BLE001 - we want the bench to keep going
        report.duration_ms = round((time.perf_counter() - started) * 1000, 2)
        report.parse_error = f"{type(err).__name__}: {err}"
        return report

    report.duration_ms = round((time.perf_counter() - started) * 1000, 2)
    data = result.data
    report.family = data.get("family")
    report.model = data.get("model") or ""
    report.size = data.get("size") or ""
    report.type = data.get("type") or ""
    report.designation_found = bool(data.get("designation_code"))
    report.warning_codes = [w.get("code", "") for w in data.get("warnings") or []]
    report.field_presence = _field_presence(data)

    schema_errors = list(validator.iter_errors(data))
    if schema_errors:
        report.schema_errors = [e.message for e in schema_errors[:5]]
    report.schema_valid = not schema_errors
    return report


def _aggregate(corpus_root: Path, fiches: list[FicheReport]) -> BenchReport:
    report = BenchReport(corpus_root=str(corpus_root), fiches=fiches, total=len(fiches))
    if not fiches:
        return report

    durations = [f.duration_ms for f in fiches]
    report.duration_ms_stats = {
        "min": round(min(durations), 2),
        "p50": round(statistics.median(durations), 2),
        "p95": round(_percentile(durations, 0.95), 2),
        "max": round(max(durations), 2),
    }

    family_counter: Counter[str] = Counter()
    warnings_counter: Counter[str] = Counter()
    section_totals: dict[str, dict[str, int]] = {
        section: dict.fromkeys(fields, 0)
        for section, fields in SECTIONS_FOR_COVERAGE
    }

    for fiche in fiches:
        if fiche.parse_error:
            report.failed += 1
            continue
        report.succeeded += 1
        if fiche.schema_valid:
            report.schema_valid_count += 1
        if fiche.designation_found:
            report.designation_found_count += 1
        if fiche.family:
            family_counter[fiche.family] += 1
        warnings_counter.update(fiche.warning_codes)
        for section, fields in SECTIONS_FOR_COVERAGE:
            presence = fiche.field_presence.get(section, {})
            for fname in fields:
                if presence.get(fname):
                    section_totals[section][fname] += 1

    report.family_distribution = dict(family_counter)
    report.warnings_top = warnings_counter.most_common(10)

    succeeded = report.succeeded or 1
    report.field_coverage = {
        section: {
            fname: round(count / succeeded, 4)
            for fname, count in fields.items()
        }
        for section, fields in section_totals.items()
    }
    return report


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = q * (len(ordered) - 1)
    lower = int(pos)
    upper = min(lower + 1, len(ordered) - 1)
    weight = pos - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * weight


def bench_corpus(root: Path, *, schema_path: Path | None = None) -> BenchReport:
    if schema_path is None:
        schema_path = Path("src/schema/pac_geg_schema.json")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    paths = _walk_corpus(root)
    fiches = [_bench_one(path, validator) for path in paths]
    return _aggregate(root, fiches)


def _print_human(report: BenchReport, *, strict_schema: bool) -> None:
    print(f"corpus: {report.corpus_root}")
    print(
        f"total={report.total} ok={report.succeeded} failed={report.failed} "
        f"schema_valid={report.schema_valid_count} "
        f"designation_found={report.designation_found_count}"
    )
    if report.duration_ms_stats:
        s = report.duration_ms_stats
        print(
            f"duration_ms: min={s['min']} p50={s['p50']} p95={s['p95']} max={s['max']}"
        )
    if report.family_distribution:
        print(f"families: {report.family_distribution}")
    if report.warnings_top:
        print("top warnings:")
        for code, count in report.warnings_top:
            print(f"  {count:>4} {code}")
    print("field coverage (succeeded fiches):")
    for section, fields in report.field_coverage.items():
        worst = sorted(fields.items(), key=lambda kv: kv[1])[:4]
        print(
            f"  {section}: " + ", ".join(f"{f}={p:.0%}" for f, p in worst)
            + (" ..." if len(fields) > 4 else "")
        )
    if strict_schema and report.schema_valid_count < report.succeeded:
        print(
            f"WARNING: {report.succeeded - report.schema_valid_count} fiches "
            "violate the JSON Schema (use --strict-schema to fail).",
            file=sys.stderr,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="parser-bench", description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--strict-schema",
        action="store_true",
        help="Treat schema violations as failures.",
    )
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"input path does not exist: {args.input}", file=sys.stderr)
        return 2

    report = bench_corpus(args.input)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    _print_human(report, strict_schema=args.strict_schema)
    if not report.ok:
        return 1
    if args.strict_schema and report.schema_valid_count < report.succeeded:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
