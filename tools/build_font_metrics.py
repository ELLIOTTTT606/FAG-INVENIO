"""Extract Montserrat advance widths for the fiche's text measurement.

The fiche paginates its options list before rendering, so it needs to know
how many lines a label will take. This script reads the embedded Montserrat
fonts once and stores the advance width of each Latin character (in em) so
that the app measures text without loading font files at runtime.

Usage:
    python tools/build_font_metrics.py src/services/fiche/assets \
        src/services/fiche/data/montserrat_widths.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fontTools.ttLib import TTFont

CHARACTERS = (
    [chr(c) for c in range(0x20, 0x7F)]
    + [chr(c) for c in range(0xA0, 0x180)]
    + list("‘’“”«»–—…•·€°²³µ×−")
)


def widths(font_path: Path) -> dict[str, float]:
    font = TTFont(font_path)
    units = font["head"].unitsPerEm
    cmap = font.getBestCmap()
    metrics = font["hmtx"].metrics
    result = {}
    for char in CHARACTERS:
        glyph = cmap.get(ord(char))
        if glyph is not None:
            result[char] = round(metrics[glyph][0] / units, 4)
    return result


def main() -> None:
    assets, target = Path(sys.argv[1]), Path(sys.argv[2])
    data = {str(w): widths(assets / f"montserrat-{w}.woff2") for w in (400, 600)}
    target.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), "utf-8")
    print(f"wrote {target} ({target.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
