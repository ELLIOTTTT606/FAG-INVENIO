"""Snapshots of the GALLETTI options referential and their comparison.

The referential is built once from the GALLETTI configurator, then refreshed:
each refresh takes a new snapshot and compares it with the previous one to
report what was added, modified or removed, machine by machine. This module
is the comparison engine behind that "Actualiser" step; how a snapshot is
taken (Baserow today, the configurator tomorrow) stays outside of it.

A snapshot is a JSON document:

    {"taken_at": "2026-11-16T09:00:00+00:00",
     "options": [{"model": "PLP", "type": "HS", "size": "052", "code": "1",
                  "category": "...", "label": "...", "price_eur": 129.0, ...}]}
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from src.services.options_catalog import OptionsCatalog

__all__ = [
    "COMPARED_FIELDS",
    "FieldChange",
    "OptionChange",
    "ReferentialDiff",
    "diff_snapshots",
    "take_snapshot",
]

Key = tuple[str, str, str, str]  # model, type, size, option code

COMPARED_FIELDS = (
    "category",
    "label",
    "description",
    "tips",
    "price_eur",
    "available",
    "current_A",
    "available_pressure_kPa",
)

_FIELD_LABELS = {
    "category": "catégorie",
    "label": "libellé",
    "description": "description",
    "tips": "conseil",
    "price_eur": "prix",
    "available": "disponibilité",
    "current_A": "intensité",
    "available_pressure_kPa": "pression disponible",
}


def _key(option: dict[str, Any]) -> Key:
    return tuple(  # type: ignore[return-value]
        str(option.get(name) or "").strip().upper() for name in ("model", "type", "size", "code")
    )


def _normalise(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = " ".join(value.split())
        return stripped or None
    return value


def _same(old: Any, new: Any) -> bool:
    old, new = _normalise(old), _normalise(new)
    if isinstance(old, int | float) and isinstance(new, int | float):
        if isinstance(old, bool) or isinstance(new, bool):
            return old is new
        return math.isclose(float(old), float(new), abs_tol=0.005)
    return bool(old == new)


@dataclass(frozen=True)
class FieldChange:
    field: str
    old: Any
    new: Any


@dataclass(frozen=True)
class OptionChange:
    key: Key
    label: str
    changes: tuple[FieldChange, ...]


@dataclass
class ReferentialDiff:
    added: list[dict[str, Any]] = field(default_factory=list)
    removed: list[dict[str, Any]] = field(default_factory=list)
    changed: list[OptionChange] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not (self.added or self.removed or self.changed)

    def summary(self) -> str:
        if self.is_empty:
            return "Référentiel à jour : aucune différence."
        return (
            f"{len(self.added)} ajout(s), {len(self.changed)} modification(s), "
            f"{len(self.removed)} suppression(s)."
        )

    def to_markdown(self) -> str:
        """French report, grouped by machine."""

        lines = ["# Actualisation du référentiel GALLETTI", "", self.summary(), ""]
        machines = sorted(
            {_key(o)[:3] for o in self.added}
            | {_key(o)[:3] for o in self.removed}
            | {c.key[:3] for c in self.changed}
        )
        for machine in machines:
            lines.append(f"## {' '.join(part for part in machine if part)}")
            lines.append("")
            for option in sorted(self.added, key=_key):
                if _key(option)[:3] == machine:
                    lines.append(f"- **Ajout** `{option.get('code')}` {option.get('label', '')}")
            for change in sorted(self.changed, key=lambda c: c.key):
                if change.key[:3] == machine:
                    details = "; ".join(
                        f"{_FIELD_LABELS.get(c.field, c.field)} : {_show(c.old)} → {_show(c.new)}"
                        for c in change.changes
                    )
                    lines.append(f"- **Modification** `{change.key[3]}` {change.label} ({details})")
            for option in sorted(self.removed, key=_key):
                if _key(option)[:3] == machine:
                    lines.append(
                        f"- **Suppression** `{option.get('code')}` {option.get('label', '')}"
                    )
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"


def _show(value: Any) -> str:
    value = _normalise(value)
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "oui" if value else "non"
    return str(value)


def _index(options: Iterable[dict[str, Any]]) -> dict[Key, dict[str, Any]]:
    index: dict[Key, dict[str, Any]] = {}
    for option in options:
        key = _key(option)
        if not key[3]:
            continue  # an option without code cannot be followed over time
        index[key] = option
    return index


def diff_snapshots(
    old: Iterable[dict[str, Any]], new: Iterable[dict[str, Any]]
) -> ReferentialDiff:
    """Compare two lists of options (each carrying model, type, size and code)."""

    before, after = _index(old), _index(new)
    diff = ReferentialDiff()
    for key in sorted(after.keys() - before.keys()):
        diff.added.append(after[key])
    for key in sorted(before.keys() - after.keys()):
        diff.removed.append(before[key])
    for key in sorted(before.keys() & after.keys()):
        changes = tuple(
            FieldChange(name, before[key].get(name), after[key].get(name))
            for name in COMPARED_FIELDS
            if not _same(before[key].get(name), after[key].get(name))
        )
        if changes:
            label = str(after[key].get("label") or before[key].get("label") or "")
            diff.changed.append(OptionChange(key=key, label=label, changes=changes))
    return diff


def take_snapshot(
    catalog: OptionsCatalog,
    machines: Iterable[tuple[str, str, str]],
    taken_at: datetime | None = None,
) -> dict[str, Any]:
    """Read the options of every (model, type, size) from a catalogue."""

    options = []
    for model, type_, size in machines:
        for option in catalog.list_options(model, type_, size):
            options.append({"model": model, "type": type_, "size": size, **option.to_dict()})
    return {
        "taken_at": (taken_at or datetime.now(tz=UTC)).isoformat(),
        "options": options,
    }
