"""Decoding of the GALLETTI designation string into structured options.

A GALLETTI designation looks like:

    PLP052HS2B A000CE000I00110 0000000I000000000000

The first token is the prefix (`Model + Size + HeatCool + Acoustic + suffix`),
already covered by `DESIGNATION_RE` in `_common.py`. The next two tokens are
`block1` (typically 15 chars) and `block2` (typically 20 chars). Each
character at a given position encodes a configuration option (pump,
antifreeze kit, communication card, low-noise level, etc.).

Decoding is *position-based* and *family-aware*: for a given `(family,
block, position, character)`, a row in `designation_decoder.csv` provides
the option code, category, label, description and tips. The mapping is
expected to be filled in by the FA team from the Baserow OPTIONS et
ACCESSOIRES table.

When no decoder row matches, this module falls back to a placeholder:

    {
      "code": "B1P04",
      "category": "designation",
      "label": "Option codee position B1P04 = 'C' (a renseigner)",
      "selected": True,
      "block": 1,
      "position": 4,
      "character": "C",
      "decoded": False
    }

This way a human reviewer in INVENIO can see *which* positions are non-zero
in the designation and complete the catalog incrementally.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.parser._common import DESIGNATION_RE

DEFAULT_CHARACTER = "0"


@dataclass(frozen=True)
class DecoderRule:
    family: str
    block: int
    position: int
    character: str
    code: str
    category: str
    label_fr: str
    description_fr: str
    tips_fr: str


@dataclass
class Decoder:
    """Mapping `(family, block, position, character)` -> DecoderRule."""

    rules: dict[tuple[str, int, int, str], DecoderRule]

    @classmethod
    def empty(cls) -> Decoder:
        return cls(rules={})

    def lookup(
        self, family: str, block: int, position: int, character: str
    ) -> DecoderRule | None:
        return self.rules.get((family, block, position, character))


def load_decoder(path: Path) -> Decoder:
    """Read a `designation_decoder.csv`. Missing or empty file -> empty decoder."""

    if not path.exists():
        return Decoder.empty()

    rules: dict[tuple[str, int, int, str], DecoderRule] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return Decoder.empty()
        for row in reader:
            try:
                family = (row["family"] or "").strip().upper()
                block = int(row["block"])
                position = int(row["position"])
                character = (row["character"] or "").strip()
            except (KeyError, ValueError):
                continue
            if not character:
                continue
            rules[(family, block, position, character)] = DecoderRule(
                family=family,
                block=block,
                position=position,
                character=character,
                code=(row.get("code") or "").strip(),
                category=(row.get("category") or "").strip(),
                label_fr=(row.get("label_fr") or "").strip(),
                description_fr=(row.get("description_fr") or "").strip(),
                tips_fr=(row.get("tips_fr") or "").strip(),
            )
    return Decoder(rules=rules)


def parse_blocks(designation: str | None) -> dict[str, str | None]:
    """Return `{ "block1": ..., "block2": ... }` from a designation string."""

    if not designation:
        return {"block1": None, "block2": None}
    match = DESIGNATION_RE.search(designation)
    if not match:
        return {"block1": None, "block2": None}
    return {"block1": match.group("block1"), "block2": match.group("block2")}


def _placeholder_option(block: int, position: int, character: str) -> dict[str, Any]:
    code = f"B{block}P{position:02d}"
    return {
        "code": code,
        "category": "designation",
        "label": f"Option codee position {code} = '{character}' (a renseigner)",
        "description": None,
        "tips": None,
        "selected": True,
        "block": block,
        "position": position,
        "character": character,
        "decoded": False,
    }


def _decoded_option(rule: DecoderRule) -> dict[str, Any]:
    return {
        "code": rule.code or f"B{rule.block}P{rule.position:02d}",
        "category": rule.category or "designation",
        "label": rule.label_fr
        or f"Option codee position B{rule.block}P{rule.position:02d}",
        "description": rule.description_fr or None,
        "tips": rule.tips_fr or None,
        "selected": True,
        "block": rule.block,
        "position": rule.position,
        "character": rule.character,
        "decoded": True,
    }


def decode_options(
    designation: str | None,
    family: str,
    decoder: Decoder | None = None,
) -> list[dict[str, Any]]:
    """Walk both blocks; emit one entry per non-default character."""

    blocks = parse_blocks(designation)
    options: list[dict[str, Any]] = []
    decoder = decoder or Decoder.empty()
    for block_idx, block_key in [(1, "block1"), (2, "block2")]:
        block = blocks.get(block_key) or ""
        for position, character in enumerate(block):
            if character == DEFAULT_CHARACTER:
                continue
            rule = decoder.lookup(family, block_idx, position, character)
            if rule is not None:
                options.append(_decoded_option(rule))
            else:
                options.append(_placeholder_option(block_idx, position, character))
    return options
