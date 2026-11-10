"""Pré-analyse d'une demande (CCTP, mail client) pour INVENIO.

Envoie le texte de la demande à un LLM (via le client agnostique) avec un
prompt structuré, et renvoie une analyse au format fixe attendu par les
commerciaux France Air : conditions, type préconisé, puissances, implantation,
options, et une conclusion/préconisation produit GALLETTI.
"""

from __future__ import annotations

import json
import re
from typing import Any

from src.services.llm_client import LLMClient, LLMError

_SYSTEM_PROMPT = """Tu es un ingénieur d'application CVC (chauffage, ventilation, \
climatisation) chez France Air, expert des pompes à chaleur (PAC) et groupes d'eau \
glacée (GEG), notamment de la gamme GALLETTI.

On te donne le texte brut d'une demande client (CCTP, mail, note). Ta tâche :
analyser la partie thermodynamique (PAC / groupe d'eau glacée) et produire une
synthèse structurée pour aider le commercial à sélectionner un produit.

Règles :
- Ne rajoute JAMAIS d'informations qui ne sont pas dans la demande. Si une donnée
  est absente, mets null (ne devine pas une valeur chiffrée).
- Les puissances et températures doivent venir du texte. Si le texte donne une
  plage, garde-la en texte.
- Pour la préconisation produit, tu peux raisonner à partir de ton expertise
  (type de machine adapté, fourchette de taille) mais reste prudent et explique.
- Réponds UNIQUEMENT avec un objet JSON valide, sans texte autour, au schéma exact
  demandé par l'utilisateur."""

_USER_TEMPLATE = """Voici la demande à analyser :

<<<DEMANDE>>>
{demand}
<<<FIN DEMANDE>>>

Réponds avec CE schéma JSON exact (toutes les clés présentes, null si inconnu) :

{{
  "resume": "une phrase résumant le besoin",
  "conditions": {{
    "exterieur_ete": "temp air ext été (°C) ou null",
    "exterieur_hiver": "temp air ext hiver (°C) ou null",
    "interieur_ete": "consigne intérieure été ou null",
    "interieur_hiver": "consigne intérieure hiver ou null",
    "regime_eau_froid": "régime d'eau froide, ex '7/12°C' ou null",
    "regime_eau_chaud": "régime d'eau chaude, ex '45/40°C' ou null",
    "autres": "autres conditions (glycol, altitude, acoustique…) ou null"
  }},
  "puissances": {{
    "froid_kw": "puissance froid attendue en kW (nombre ou plage) ou null",
    "chaud_kw": "puissance chaud attendue en kW (nombre ou plage) ou null",
    "autres": "autres exigences de perf (EER/COP/SCOP mini…) ou null"
  }},
  "type_preconise": {{
    "famille": "type de machine (ex 'PAC air/eau réversible', 'groupe d'eau glacée') ou null",
    "marque": "marque si imposée dans la demande, sinon null",
    "modele": "modèle GALLETTI préconisé si tu peux, sinon null",
    "taille": "fourchette de taille/puissance adaptée ou null",
    "justification": "pourquoi ce type (1-2 phrases)"
  }},
  "implantation": "contraintes d'implantation (intérieur/extérieur, toiture, local technique, encombrement, acoustique voisinage…) ou null",
  "options": ["liste des options/accessoires demandés ou utiles (pompes, réservoir tampon, kit hydraulique, désurchauffeur, grille anti-intrusion…)"],
  "fluide": "fluide frigorigène demandé/contraint (ex R32, R454B) ou null",
  "conclusion": {{
    "propositions": [
      {{
        "produit": "produit/gamme GALLETTI proposé",
        "avantages": "avantages",
        "inconvenients": "inconvénients / points d'attention"
      }}
    ],
    "recommandation": "ta recommandation finale en 2-3 phrases",
    "questions": ["questions à poser au client pour affiner (points manquants)"]
  }}
}}"""


def _extract_json(text: str) -> dict[str, Any]:
    """Extrait le 1er objet JSON d'une réponse LLM (robuste aux fences / texte)."""
    # Retire d'éventuels fences ```json ... ```
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    candidate = fenced.group(1) if fenced else text
    try:
        return dict(json.loads(candidate))
    except (json.JSONDecodeError, ValueError):
        pass
    # Dernier recours : du premier { au dernier }
    start, end = candidate.find("{"), candidate.rfind("}")
    if start != -1 and end > start:
        try:
            return dict(json.loads(candidate[start : end + 1]))
        except (json.JSONDecodeError, ValueError) as err:
            raise LLMError(f"Réponse LLM non-JSON : {err}") from err
    raise LLMError("Réponse LLM ne contient pas de JSON exploitable.")


def analyze_demand(text: str, *, llm: LLMClient) -> dict[str, Any]:
    """Analyse le texte d'une demande et renvoie la synthèse structurée."""
    demand = text.strip()
    if not demand:
        raise LLMError("Demande vide : rien à analyser.")
    # Garde-fou taille (évite d'envoyer un pavé démesuré)
    if len(demand) > 60_000:
        demand = demand[:60_000]
    content = llm.chat(
        system=_SYSTEM_PROMPT,
        user=_USER_TEMPLATE.format(demand=demand),
        json_mode=True,
        max_tokens=4096,
    )
    result = _extract_json(content)
    result["_meta"] = {"chars_analyzed": len(demand)}
    return result
