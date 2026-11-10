"""Tests de la pré-analyse de demande (Phase 2)."""

from __future__ import annotations

import pytest

from src.services.demand_analyzer import _extract_json, analyze_demand
from src.services.llm_client import LLMClient, LLMConfig, LLMError


def test_extract_json_plain() -> None:
    assert _extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_fenced() -> None:
    assert _extract_json('```json\n{"a": 1, "b": "x"}\n```') == {"a": 1, "b": "x"}


def test_extract_json_with_surrounding_text() -> None:
    text = 'Voici le résultat :\n{"a": 1}\nMerci.'
    assert _extract_json(text) == {"a": 1}


def test_extract_json_invalid_raises() -> None:
    with pytest.raises(LLMError):
        _extract_json("pas de json ici")


class _StubLLM(LLMClient):
    def __init__(self, response: str) -> None:
        super().__init__(LLMConfig(base_url="x", model="y"))
        self._response = response

    def chat(self, *, system: str, user: str, json_mode: bool = False, max_tokens: int = 4096) -> str:
        return self._response


def test_analyze_demand_parses_and_adds_meta() -> None:
    stub = _StubLLM('{"resume": "PAC 50 kW", "type_preconise": {"famille": "PAC air/eau"}}')
    result = analyze_demand("Besoin PAC 50 kW régime 45/40", llm=stub)
    assert result["resume"] == "PAC 50 kW"
    assert result["type_preconise"]["famille"] == "PAC air/eau"
    assert result["_meta"]["chars_analyzed"] > 0


def test_analyze_demand_empty_raises() -> None:
    stub = _StubLLM("{}")
    with pytest.raises(LLMError):
        analyze_demand("   ", llm=stub)
