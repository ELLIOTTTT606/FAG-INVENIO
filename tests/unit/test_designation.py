"""Tests for designation block decoding."""

from __future__ import annotations

from pathlib import Path

from src.parser.designation import (
    Decoder,
    decode_options,
    load_decoder,
    parse_blocks,
)

PAC_DESIGNATION = "PLP052HS2B A000CE000I00110 0000000I000000000000"
GEG_DESIGNATION_ALL_ZERO = "VLS202CS0A 000000000000000 00000000000000000000"


def test_parse_blocks_extracts_both_blocks() -> None:
    blocks = parse_blocks(PAC_DESIGNATION)
    assert blocks["block1"] == "A000CE000I00110"
    assert blocks["block2"] == "0000000I000000000000"


def test_parse_blocks_returns_nones_when_designation_invalid() -> None:
    assert parse_blocks(None) == {"block1": None, "block2": None}
    assert parse_blocks("not a designation") == {"block1": None, "block2": None}


def test_decode_options_returns_placeholder_per_non_zero_position() -> None:
    options = decode_options(PAC_DESIGNATION, family="PAC")

    assert options, "expected at least one non-zero position"
    for opt in options:
        assert opt["selected"] is True
        assert opt["decoded"] is False
        assert opt["block"] in (1, 2)
        assert isinstance(opt["position"], int)
        assert opt["character"] != "0"
        assert opt["code"].startswith("B")
        assert opt["category"] == "designation"

    block_chars = {(o["block"], o["position"]): o["character"] for o in options}
    assert block_chars[(1, 0)] == "A"
    assert block_chars[(1, 4)] == "C"
    assert block_chars[(1, 5)] == "E"
    assert block_chars[(1, 9)] == "I"
    assert block_chars[(1, 12)] == "1"
    assert block_chars[(1, 13)] == "1"
    assert block_chars[(2, 7)] == "I"


def test_decode_options_returns_empty_when_all_zero() -> None:
    options = decode_options(GEG_DESIGNATION_ALL_ZERO, family="GEG")
    assert options == []


def test_decode_options_uses_decoder_when_match_exists(tmp_path: Path) -> None:
    csv_path = tmp_path / "decoder.csv"
    csv_path.write_text(
        "family,block,position,character,code,category,label_fr,description_fr,tips_fr\n"
        "PAC,1,0,A,A,Compresseur,Scroll modulant,Compresseur scroll modulant inverter,Verifier alim\n"
        "PAC,1,4,C,C,Vanne,Detendeur electronique,Vanne d'expansion electronique,\n",
        encoding="utf-8",
    )
    decoder = load_decoder(csv_path)
    options = decode_options(PAC_DESIGNATION, family="PAC", decoder=decoder)

    decoded = [o for o in options if o["decoded"]]
    placeholders = [o for o in options if not o["decoded"]]

    assert len(decoded) == 2
    by_pos = {(o["block"], o["position"]): o for o in decoded}
    assert by_pos[(1, 0)]["label"] == "Scroll modulant"
    assert by_pos[(1, 0)]["description"] == "Compresseur scroll modulant inverter"
    assert by_pos[(1, 0)]["tips"] == "Verifier alim"
    assert by_pos[(1, 4)]["label"] == "Detendeur electronique"

    assert len(placeholders) == len(options) - 2
    assert all(o["decoded"] is False for o in placeholders)


def test_load_decoder_returns_empty_for_missing_file(tmp_path: Path) -> None:
    decoder = load_decoder(tmp_path / "does_not_exist.csv")
    assert isinstance(decoder, Decoder)
    assert decoder.rules == {}


def test_load_decoder_skips_invalid_rows(tmp_path: Path) -> None:
    csv_path = tmp_path / "decoder.csv"
    csv_path.write_text(
        "family,block,position,character,code,category,label_fr,description_fr,tips_fr\n"
        "PAC,not-int,0,A,A,Cat,Label,Desc,Tip\n"
        "PAC,1,0,,A,Cat,Label,Desc,Tip\n"
        "PAC,1,0,A,A,Cat,Label,Desc,Tip\n",
        encoding="utf-8",
    )
    decoder = load_decoder(csv_path)
    assert list(decoder.rules.keys()) == [("PAC", 1, 0, "A")]


def test_decode_options_placeholder_code_is_well_formed() -> None:
    options = decode_options(PAC_DESIGNATION, family="PAC")
    placeholder = next(o for o in options if (o["block"], o["position"]) == (1, 12))
    assert placeholder["code"] == "B1P12"
    assert "B1P12" in placeholder["label"]
