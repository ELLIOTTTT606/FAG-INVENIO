"""Pre-compute the department outlines used by the fiche's contacts map.

Source: the simplified French departments GeoJSON published at
https://github.com/gregoiredavid/france-geojson
(``departements-version-simplifiee.geojson``).

The fiche never needs geographic coordinates, only SVG path strings, so this
script projects the outlines once (equirectangular, longitudes scaled by
cos 46.5 deg), simplifies them (Douglas-Peucker) and writes a compact JSON file
that ships with the app.

Usage:
    python tools/build_france_map.py departements-version-simplifiee.geojson \
        src/services/fiche/data/france_departements.json
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

MAP_WIDTH = 520.0
TOLERANCE = 0.6  # map units (the map is 520 units wide, about 134 mm on paper)


def _project(lon: float, lat: float) -> tuple[float, float]:
    return lon * math.cos(math.radians(46.5)), -lat


def _rings(geometry: dict) -> list[list[list[float]]]:
    if geometry["type"] == "MultiPolygon":
        return [poly[0] for poly in geometry["coordinates"]]
    return [geometry["coordinates"][0]]


def _simplify(points: list[tuple[float, float]], tolerance: float) -> list[tuple[float, float]]:
    if len(points) < 4:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        start, end = stack.pop()
        (x1, y1), (x2, y2) = points[start], points[end]
        dx, dy = x2 - x1, y2 - y1
        norm = math.hypot(dx, dy) or 1e-9
        index, dmax = -1, 0.0
        for i in range(start + 1, end):
            x0, y0 = points[i]
            d = abs(dy * x0 - dx * y0 + x2 * y1 - y2 * x1) / norm
            if d > dmax:
                index, dmax = i, d
        if dmax > tolerance and index > 0:
            keep[index] = True
            stack.append((start, index))
            stack.append((index, end))
    return [p for p, k in zip(points, keep, strict=True) if k]


def build(source: Path) -> dict:
    features = json.loads(source.read_text(encoding="utf-8"))["features"]
    projected = [
        (feature, [[_project(*p[:2]) for p in ring] for ring in _rings(feature["geometry"])])
        for feature in features
    ]
    xs = [x for _, rings in projected for ring in rings for x, _ in ring]
    ys = [y for _, rings in projected for ring in rings for _, y in ring]
    min_x, min_y = min(xs), min(ys)
    scale = MAP_WIDTH / (max(xs) - min_x)
    height = (max(ys) - min_y) * scale

    departments = []
    for feature, rings in projected:
        parts = []
        for ring in rings:
            points = [((x - min_x) * scale, (y - min_y) * scale) for x, y in ring]
            # A closed ring starts and ends on the same point, which gives
            # Douglas-Peucker a degenerate baseline: simplify two open halves.
            mid = len(points) // 2
            points = _simplify(points[: mid + 1], TOLERANCE)[:-1] + _simplify(points[mid:], TOLERANCE)
            if len(points) < 3:
                continue
            parts.append("M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in points) + "Z")
        departments.append(
            {
                "code": feature["properties"]["code"],
                "name": feature["properties"]["nom"],
                "d": "".join(parts),
            }
        )
    departments.sort(key=lambda d: d["code"])
    return {"width": MAP_WIDTH, "height": round(height, 1), "departments": departments}


def main() -> None:
    source, target = Path(sys.argv[1]), Path(sys.argv[2])
    target.write_text(json.dumps(build(source), ensure_ascii=False, separators=(",", ":")), "utf-8")
    print(f"wrote {target} ({target.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
