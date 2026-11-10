"""Client pour le configurateur GALLETTI (offer.gallettigroup.com).

Ce module pilote l'application web GALLETTI « Quality Selector » via ses
endpoints HTTP, repérés par capture réseau (HAR). Il ne s'agit pas d'une API
REST publique : l'application est rendue côté serveur (ASP.NET) et renvoie
surtout du HTML, plus quelques endpoints JSON.

Phase 1 — ce que ce client couvre :
    * ``list_projects()``  -> liste les projets (= « offerte ») de l'onglet
      Gestione/Offerta, en parsant la table HTML ``#dtOfferte``.

Endpoints repérés (pour mémoire / phases suivantes) :
    GET  /Gestione/Offerta?tipoProgetto=1            -> page liste projets (HTML)
    GET  /Gestione/Offerta/Offerta/{id}             -> détail d'un projet (HTML)
    POST /Configuratore/Wizard/EseguiCalcoloPrestazioni -> calcul perf (HTML)
    POST /Configuratore/Wizard/SalvaRisultatoCalcolo    -> résultat structuré (JSON)
    POST /Configuratore/Wizard/GetOpzioniAccessoriVarianti -> options (JSON)
    GET  /Gestione/Offerta/StampaOfferta            -> génération fiche Galletti

Authentification
----------------
Les endpoints exigent une session authentifiée. Pour un usage personnel /
apprentissage, on fournit le **cookie de session** du navigateur via la
configuration (variable d'env ``GALLETTI_COOKIE``), jamais en dur dans le code.
Le cookie expire : il faut le renouveler quand les appels renvoient une page de
login. Un login programmatique (identifiant/mot de passe) pourra être ajouté
plus tard.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser

import httpx

DEFAULT_BASE_URL = "https://offer.gallettigroup.com"

# id interne du projet, extrait de onclick="readOnlyOfferta(306090);"
_PROJECT_ID_RE = re.compile(r"readOnlyOfferta\((\d+)\)")


class GallettiError(RuntimeError):
    """Erreur renvoyée par le configurateur GALLETTI ou le client."""


class GallettiAuthError(GallettiError):
    """La session n'est pas (ou plus) authentifiée : cookie absent/expiré."""


@dataclass(frozen=True)
class GallettiConfig:
    """Configuration d'accès au configurateur GALLETTI."""

    base_url: str = DEFAULT_BASE_URL
    session_cookie: str = ""
    timeout_seconds: float = 30.0

    @property
    def live(self) -> bool:
        """True quand un cookie de session est fourni."""
        return bool(self.session_cookie.strip())

    @property
    def headers(self) -> dict[str, str]:
        hdrs = {
            "User-Agent": "Mozilla/5.0 (compatible; INVENIO/0.1)",
            "Accept": "text/html,application/json,*/*",
            "X-Requested-With": "XMLHttpRequest",
        }
        if self.session_cookie:
            hdrs["Cookie"] = self.session_cookie
        return hdrs


@dataclass(frozen=True)
class GallettiProject:
    """Une ligne de l'onglet « Projets » (= une offerta)."""

    id: int
    numero: str
    date: str
    client: str
    nom: str
    utilisateur: str
    prix_total: str

    def to_dict(self) -> dict[str, str | int]:
        return {
            "id": self.id,
            "numero": self.numero,
            "date": self.date,
            "client": self.client,
            "nom": self.nom,
            "utilisateur": self.utilisateur,
            "prix_total": self.prix_total,
        }


class _OfferteTableParser(HTMLParser):
    """Extrait les lignes de la table ``#dtOfferte`` (liste des projets).

    On ne dépend d'aucune lib tierce : la table est server-rendered et sa
    structure est stable (colonnes fixes). On capture, pour chaque ``<tr>`` du
    ``<tbody>``, le texte de chaque ``<td>`` plus l'id interne du projet trouvé
    dans un ``onclick="readOnlyOfferta(<id>)"``.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._in_target_table = False
        self._table_depth = 0
        self._in_tbody = False
        self._in_row = False
        self._in_cell = False
        self._cell_text: list[str] = []
        self._row_cells: list[str] = []
        self._row_html_onclicks: list[str] = []
        self.rows: list[tuple[list[str], list[str]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        ad = dict(attrs)
        if tag == "table":
            self._table_depth += 1
            if (ad.get("id") or "") == "dtOfferte":
                self._in_target_table = True
        elif self._in_target_table and tag == "tbody":
            self._in_tbody = True
        elif self._in_target_table and self._in_tbody and tag == "tr":
            self._in_row = True
            self._row_cells = []
            self._row_html_onclicks = []
        elif self._in_row and tag == "td":
            self._in_cell = True
            self._cell_text = []
        # capture tout onclick de la ligne (contient readOnlyOfferta(id))
        if self._in_row:
            onclick = ad.get("onclick")
            if onclick:
                self._row_html_onclicks.append(onclick)

    def handle_endtag(self, tag: str) -> None:
        if tag == "td" and self._in_cell:
            text = " ".join("".join(self._cell_text).split())
            self._row_cells.append(text)
            self._in_cell = False
        elif tag == "tr" and self._in_row:
            if self._row_cells:
                self.rows.append((self._row_cells, self._row_html_onclicks))
            self._in_row = False
        elif tag == "tbody" and self._in_tbody:
            self._in_tbody = False
        elif tag == "table":
            if self._in_target_table and self._table_depth == 1:
                self._in_target_table = False
            self._table_depth = max(0, self._table_depth - 1)

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell_text.append(data)


def parse_projects_html(html: str) -> list[GallettiProject]:
    """Parse le HTML de ``/Gestione/Offerta`` en liste de projets.

    Colonnes de ``#dtOfferte`` (ordre fixe) :
        0 Statut · 1 N° projet · 2 Date · 3 Client · 4 Nom du projet ·
        5 Utilisateur · 6 Total Prix · 7 Actions
    """
    parser = _OfferteTableParser()
    parser.feed(html)

    projects: list[GallettiProject] = []
    for cells, onclicks in parser.rows:
        pid = _extract_project_id(onclicks)
        if pid is None:
            continue
        projects.append(
            GallettiProject(
                id=pid,
                numero=_col(cells, 1),
                date=_col(cells, 2),
                client=_col(cells, 3),
                nom=_col(cells, 4),
                utilisateur=_col(cells, 5),
                prix_total=_col(cells, 6),
            )
        )
    return projects


def _extract_project_id(onclicks: list[str]) -> int | None:
    for oc in onclicks:
        m = _PROJECT_ID_RE.search(oc)
        if m:
            return int(m.group(1))
    return None


def _col(cells: list[str], idx: int) -> str:
    return cells[idx] if idx < len(cells) else ""


def _looks_like_login(html: str) -> bool:
    low = html.lower()
    return ("name=\"password\"" in low or "type=\"password\"" in low) and "dtofferte" not in low


class GallettiSelectorClient:
    """Client HTTP minimal pour le configurateur GALLETTI."""

    def __init__(self, config: GallettiConfig) -> None:
        self._config = config

    def _client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self._config.base_url,
            headers=self._config.headers,
            timeout=self._config.timeout_seconds,
            follow_redirects=True,
        )

    def _get_html(self, path: str, params: dict[str, str] | None = None) -> str:
        if not self._config.live:
            raise GallettiAuthError(
                "Aucun cookie de session GALLETTI (GALLETTI_COOKIE) : "
                "impossible d'interroger le configurateur."
            )
        try:
            with self._client() as client:
                resp = client.get(path, params=params)
        except httpx.HTTPError as err:
            raise GallettiError(f"Erreur réseau GALLETTI sur {path!r}: {err}") from err
        if resp.status_code in (401, 403):
            raise GallettiAuthError(
                f"Accès refusé ({resp.status_code}) sur {path!r} : cookie expiré ?"
            )
        if resp.status_code >= 400:
            raise GallettiError(f"GALLETTI {resp.status_code} sur {path!r}.")
        html = resp.text
        if _looks_like_login(html):
            raise GallettiAuthError(
                f"Réponse de login reçue sur {path!r} : session expirée, "
                "renouvelle le cookie GALLETTI_COOKIE."
            )
        return html

    def list_projects(self, *, tipo_progetto: int = 1) -> list[GallettiProject]:
        """Liste les projets (offerte) de l'onglet Gestione/Offerta."""
        html = self._get_html("/Gestione/Offerta", params={"tipoProgetto": str(tipo_progetto)})
        return parse_projects_html(html)


def make_client_from_env() -> GallettiSelectorClient:
    """Construit un client depuis la configuration d'environnement."""
    from src.services.settings import get_settings

    settings = get_settings()
    config = GallettiConfig(
        base_url=settings.galletti_base_url or DEFAULT_BASE_URL,
        session_cookie=settings.galletti_cookie,
        timeout_seconds=settings.galletti_timeout_seconds,
    )
    return GallettiSelectorClient(config)
