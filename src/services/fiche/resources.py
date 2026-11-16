"""Static resources of the fiche: fonts, logos, photos, map and range documentation.

Everything is embedded as data URLs so the rendered HTML is self-contained:
the same string feeds the in-app preview (an iframe ``srcdoc``), the
browser's print dialog and WeasyPrint.
"""

from __future__ import annotations

import base64
import json
import re
from functools import lru_cache
from importlib import resources
from typing import Any

_PACKAGE = "src.services.fiche"

_MEDIA_TYPES = {
    ".png": "image/png",
    ".webp": "image/webp",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".woff2": "font/woff2",
}

_MODEL_RE = re.compile(r"^[A-Za-z0-9_-]{1,32}$")


def _files() -> Any:
    return resources.files(_PACKAGE)


@lru_cache(maxsize=32)
def asset_data_url(name: str) -> str:
    """Return ``assets/<name>`` as a base64 data URL."""

    suffix = name[name.rfind(".") :].lower()
    media_type = _MEDIA_TYPES[suffix]
    payload = _files().joinpath("assets").joinpath(name).read_bytes()
    return f"data:{media_type};base64,{base64.b64encode(payload).decode('ascii')}"


@lru_cache(maxsize=1)
def france_map() -> dict[str, Any]:
    """Pre-projected department outlines (see ``tools/build_france_map.py``)."""

    raw = _files().joinpath("data").joinpath("france_departements.json").read_text("utf-8")
    return json.loads(raw)


@lru_cache(maxsize=1)
def font_widths() -> dict[str, dict[str, float]]:
    """Montserrat advance widths in em, by weight (see ``tools/build_font_metrics.py``)."""

    raw = _files().joinpath("data").joinpath("montserrat_widths.json").read_text("utf-8")
    return json.loads(raw)


@lru_cache(maxsize=16)
def _range_doc(model: str) -> dict[str, Any] | None:
    entry = _files().joinpath("data").joinpath("gammes").joinpath(f"{model}.json")
    if not entry.is_file():
        return None
    return json.loads(entry.read_text("utf-8"))


def range_documentation(model: str | None) -> dict[str, Any] | None:
    """Documentation of a GALLETTI range (``PLP`` ...), or None when not written yet."""

    if not model or not _MODEL_RE.match(model):
        return None
    return _range_doc(model.upper())
