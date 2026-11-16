"""Compare two snapshots of the GALLETTI options referential.

Prints (or writes) a French report of the options added, modified and removed,
machine by machine. Snapshots are JSON files as produced by
``src.services.referential.take_snapshot`` (``{"taken_at": ..., "options": [...]}``);
a bare list of options is accepted too.

Usage:
    python tools/referential_diff.py ancien.json nouveau.json
    python tools/referential_diff.py ancien.json nouveau.json --markdown rapport.md
    python tools/referential_diff.py ancien.json nouveau.json --fail-on-change
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from src.services.referential import diff_snapshots


def _options(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    options = data.get("options") if isinstance(data, dict) else data
    if not isinstance(options, list):
        raise SystemExit(f"{path}: expected a snapshot with an 'options' list")
    return [o for o in options if isinstance(o, dict)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("old", type=Path, help="previous snapshot (JSON)")
    parser.add_argument("new", type=Path, help="new snapshot (JSON)")
    parser.add_argument("--markdown", type=Path, help="write the report to this file")
    parser.add_argument(
        "--fail-on-change", action="store_true", help="exit with status 1 when anything changed"
    )
    args = parser.parse_args(argv)

    diff = diff_snapshots(_options(args.old), _options(args.new))
    report = diff.to_markdown()
    if args.markdown:
        args.markdown.write_text(report, encoding="utf-8")
        print(diff.summary())
    else:
        sys.stdout.write(report)
    return 1 if args.fail_on_change and not diff.is_empty else 0


if __name__ == "__main__":
    raise SystemExit(main())
