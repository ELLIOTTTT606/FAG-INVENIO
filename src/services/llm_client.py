"""Client LLM agnostique (API OpenAI-compatible).

Parle le format /chat/completions standard, supporté par la plupart des
fournisseurs : Groq, OpenAI, Mistral, OpenRouter, Ollama (local), etc.
On change de fournisseur en changeant seulement 3 variables d'environnement :

    LLM_BASE_URL   ex. https://api.groq.com/openai/v1   (Groq, gratuit, hébergé)
                   ex. http://localhost:11434/v1          (Ollama, local)
    LLM_API_KEY    la clé du fournisseur (vide pour Ollama local)
    LLM_MODEL      ex. llama-3.3-70b-versatile (Groq) / llama3.1 (Ollama)

Aucune dépendance SDK : un simple POST httpx.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import httpx


class LLMError(RuntimeError):
    """Erreur du fournisseur LLM ou de la configuration."""


class LLMNotConfiguredError(LLMError):
    """Aucun fournisseur LLM configuré (LLM_BASE_URL/LLM_MODEL manquants)."""


@dataclass(frozen=True)
class LLMConfig:
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    timeout_seconds: float = 60.0
    temperature: float = 0.0

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.model)


class LLMClient:
    """Client minimal pour une API /chat/completions OpenAI-compatible."""

    def __init__(self, config: LLMConfig) -> None:
        self._config = config

    def chat(
        self,
        *,
        system: str,
        user: str,
        json_mode: bool = False,
        max_tokens: int = 4096,
    ) -> str:
        """Envoie un échange system+user et renvoie le texte de la réponse."""
        if not self._config.configured:
            raise LLMNotConfiguredError(
                "LLM non configuré : définissez LLM_BASE_URL et LLM_MODEL "
                "(et LLM_API_KEY pour un fournisseur hébergé comme Groq)."
            )
        url = self._config.base_url.rstrip("/") + "/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"
        payload: dict[str, object] = {
            "model": self._config.model,
            "temperature": self._config.temperature,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            with httpx.Client(timeout=self._config.timeout_seconds) as client:
                resp = client.post(url, headers=headers, json=payload)
        except httpx.HTTPError as err:
            raise LLMError(f"Erreur réseau LLM : {err}") from err

        if resp.status_code >= 400:
            detail = resp.text[:300]
            raise LLMError(f"LLM {resp.status_code} : {detail}")

        try:
            data = resp.json()
            return str(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, ValueError, json.JSONDecodeError) as err:
            raise LLMError(f"Réponse LLM inattendue : {err}") from err


def make_llm_from_env() -> LLMClient:
    from src.services.settings import get_settings

    s = get_settings()
    return LLMClient(
        LLMConfig(
            base_url=s.llm_base_url,
            api_key=s.llm_api_key,
            model=s.llm_model,
            timeout_seconds=s.llm_timeout_seconds,
        )
    )
