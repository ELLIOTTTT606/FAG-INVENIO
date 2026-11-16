"""French number and date formatting for the fiche."""

from __future__ import annotations

from datetime import datetime
from typing import Any

NNBSP = " "  # narrow no-break space: thousands separator
NBSP = " "  # no-break space: between a value and its unit
DASH = "—"

_MONTHS = (
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
)


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def number(value: Any, unit: str = "", decimals: int | None = None) -> str:
    """Format a value the French way: ``16 259 m³/h``, ``41,7 kW``, ``—`` when missing."""

    if value is None or value == "":
        return DASH
    if isinstance(value, bool):
        text = "Oui" if value else "Non"
    elif is_number(value):
        number_ = float(value)
        if decimals is not None:
            number_ = round(number_, decimals)
        if number_.is_integer():
            text = f"{int(number_):,}".replace(",", NNBSP)
        else:
            digits = decimals if decimals is not None else 2
            text = f"{number_:,.{digits}f}".rstrip("0").rstrip(".")
            text = text.replace(",", NNBSP).replace(".", ",")
    else:
        text = str(value).strip() or DASH
    if unit and text != DASH:
        return f"{text}{NBSP}{unit}"
    return text


def long_date(moment: datetime) -> str:
    return f"{moment.day} {_MONTHS[moment.month - 1]} {moment.year}"


def short_date(moment: datetime) -> str:
    return moment.strftime("%d/%m/%Y")


def supply(raw: Any) -> str:
    """``"400 / 3+N / 50"`` -> ``"400 V · 3+N · 50 Hz"``."""

    parts = [part.strip() for part in str(raw or "").split("/")]
    if len(parts) == 3 and all(parts):
        return f"{parts[0]}{NBSP}V · {parts[1]} · {parts[2]}{NBSP}Hz"
    return number(raw)
