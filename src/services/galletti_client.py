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

import json
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser

import httpx

DEFAULT_BASE_URL = "https://offer.gallettigroup.com"

# id interne du projet, extrait de onclick="readOnlyOfferta(306090);"
_PROJECT_ID_RE = re.compile(r"readOnlyOfferta\((\d+)\)")

# Le détail d'un projet embarque ses lignes d'articles dans un
# JSON.parse('[{...}]') de la page. On repère le blob contenant "ArticoloModello".
_JSON_PARSE_RE = re.compile(r"JSON\.parse\('((?:[^'\\]|\\.)*)'\)")


class GallettiError(RuntimeError):
    """Erreur renvoyée par le configurateur GALLETTI ou le client."""


class GallettiAuthError(GallettiError):
    """La session n'est pas (ou plus) authentifiée : cookie absent/expiré."""


@dataclass(frozen=True)
class GallettiConfig:
    """Configuration d'accès au configurateur GALLETTI.

    Deux modes d'authentification :
      * ``session_cookie`` : cookie de session copié du navigateur (expire vite) ;
      * ``username`` + ``password`` : login automatique via Keycloak (recommandé).
    """

    base_url: str = DEFAULT_BASE_URL
    session_cookie: str = ""
    username: str = ""
    password: str = ""
    timeout_seconds: float = 30.0

    @property
    def live(self) -> bool:
        """True quand un mode d'auth est configuré (cookie, ou identifiants)."""
        return bool(self.session_cookie.strip()) or bool(self.username and self.password)

    @property
    def can_login(self) -> bool:
        return bool(self.username and self.password)

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


@dataclass(frozen=True)
class GallettiArticle:
    """Une ligne d'article d'un projet (machine, accessoire ou voie de dépense)."""

    position: int
    model: str
    family: str
    description: str
    price: float | None
    option_codes: list[str] = field(default_factory=list)

    @property
    def is_machine(self) -> bool:
        """True si la ligne porte un modèle (par opposition à une voie de dépense)."""
        return bool(self.model)

    def to_dict(self) -> dict[str, object]:
        return {
            "position": self.position,
            "model": self.model,
            "family": self.family,
            "description": self.description,
            "price": self.price,
            "option_codes": self.option_codes,
        }


@dataclass(frozen=True)
class GallettiProjectDetail:
    """Contenu d'un projet (offerta) : ses lignes d'articles."""

    id: int
    articles: list[GallettiArticle]

    @property
    def machines(self) -> list[GallettiArticle]:
        return [a for a in self.articles if a.is_machine]


def _split_option_codes(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [c.strip() for c in raw.split(",") if c.strip()]


def parse_project_html(html: str, *, project_id: int = 0) -> GallettiProjectDetail:
    """Parse la page détail d'un projet en liste d'articles.

    Les lignes sont embarquées dans un ``JSON.parse('[{...}]')`` de la page ;
    on repère le blob contenant ``ArticoloModello`` et on le décode.
    """
    articles: list[GallettiArticle] = []
    for m in _JSON_PARSE_RE.finditer(html):
        blob = m.group(1)
        if "ArticoloModello" not in blob:
            continue
        # Littéral JS en guillemets simples -> texte JSON : seul \' est à défaire
        # (\\uXXXX, \\/ et \\\\ restent du JSON valide).
        try:
            rows = json.loads(blob.replace("\\'", "'"))
        except (json.JSONDecodeError, ValueError):
            continue
        for idx, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                continue
            price_raw = row.get("PrezzoScontato")
            articles.append(
                GallettiArticle(
                    position=int(row.get("Posizione") or idx),
                    model=str(row.get("ArticoloModello") or ""),
                    family=str(row.get("IdFamiglia") or ""),
                    description=str(row.get("ArticoloDescrizioneTradotta") or ""),
                    price=float(price_raw) if isinstance(price_raw, int | float) else None,
                    option_codes=_split_option_codes(row.get("ListaOpzioniConfigurazione")),
                )
            )
        break  # un seul blob d'articles par page
    return GallettiProjectDetail(id=project_id, articles=articles)


# --- Résultats de calcul (page RisultatiCalcolo, table #dtParametriCalcolo) ---

# Les deux sections de tête du tableau de résultats.
_SECTION_INPUT = "Données d'Entrée"
_SECTION_OUTPUT = "Données de Sortie"
_TOP_SECTIONS = {_SECTION_INPUT, _SECTION_OUTPUT}

_TAG_RE = re.compile(r"<[^>]+>")
_TR_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_CELL_RE = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S)
_RESULTS_TABLE_RE = re.compile(
    r'<table[^>]*id="dtParametriCalcolo".*?</table>', re.S
)


def _clean_cell(raw: str) -> str:
    import html as _html

    # Déséchapper d'abord (&nbsp; -> \xa0) puis normaliser les espaces : split()
    # traite \xa0 comme un blanc, donc les espaces insécables disparaissent.
    text = _html.unescape(_TAG_RE.sub(" ", raw))
    return " ".join(text.split())


@dataclass(frozen=True)
class ResultRow:
    """Une ligne de données du tableau de résultats."""

    section: str  # "Données d'Entrée" | "Données de Sortie"
    group: str  # "Refroidissement" | "Chauffage" | "Common Data" | ...
    label: str
    unit: str
    value: str

    def to_dict(self) -> dict[str, str]:
        return {
            "section": self.section,
            "group": self.group,
            "label": self.label,
            "unit": self.unit,
            "value": self.value,
        }


@dataclass(frozen=True)
class GallettiResults:
    """Résultats de calcul d'un modèle : conditions d'entrée + performances."""

    model: str
    rows: list[ResultRow]

    def find(self, label_substr: str, *, group: str | None = None, section: str | None = None) -> str | None:
        """Retourne la 1re valeur dont le label contient ``label_substr`` (insensible casse)."""
        needle = label_substr.casefold()
        for r in self.rows:
            if group is not None and r.group != group:
                continue
            if section is not None and r.section != section:
                continue
            if needle in r.label.casefold():
                return r.value
        return None

    def to_dict(self) -> dict[str, object]:
        return {"model": self.model, "rows": [r.to_dict() for r in self.rows]}


def _num(value: str | None) -> float | None:
    """Convertit une valeur Galletti ('12.0', '9446', '-7') en float si possible."""
    if value is None:
        return None
    v = value.replace("\xa0", "").strip()
    if v in ("", "-"):
        return None
    try:
        return float(v.replace(",", "."))
    except ValueError:
        return None


def results_to_canonical(
    results: GallettiResults,
    *,
    family: str = "",
    size: str = "",
    type_: str = "HS",
) -> dict[str, object]:
    """Mappe des résultats de calcul vers le payload canonique INVENIO.

    Produit exactement les chemins attendus par le template de fiche
    (``record.conditions.cooling.water_in_C``, ``record.performance.heating.cop``…),
    afin que les données API et DOCX convergent vers le même format de fiche.
    """
    sec_in, sec_out = _SECTION_INPUT, _SECTION_OUTPUT
    cd = "Common Data"

    def cond(group: str) -> dict[str, object]:
        return {
            "water_in_C": _num(results.find("entrée eau", group=group, section=sec_in)),
            "water_out_C": _num(results.find("sortie eau", group=group, section=sec_in)),
            "air_temp_C": _num(results.find("Air exterieur", group=group, section=sec_in)),
            "load_percent": _num(results.find("Charge", group=group, section=sec_in)),
        }

    def perf(group: str) -> dict[str, object]:
        is_cool = group == "Refroidissement"
        power_label = "refroidissement" if is_cool else "chauffage"
        base: dict[str, object] = {
            "power_kW": _num(
                results.find(f"Puissance de {power_label} (", group=group, section=sec_out)
            ),
            "total_power_kW": _num(
                results.find("Puissance absorbée totale (", group=group, section=sec_out)
            ),
            "total_current_A": _num(
                results.find("Courant absorbé total (", group=group, section=sec_out)
            ),
            "water_flow_lph": _num(results.find("Débit d'eau", group=group, section=sec_out)),
            "pressure_drop_kPa": _num(
                results.find("Perte de charge", group=group, section=sec_out)
            ),
        }
        if is_cool:
            base["eer"] = _num(results.find("EER (", group=group, section=sec_out))
            base["seer"] = _num(results.find("SEER", group=group, section=sec_out))
        else:
            base["cop"] = _num(results.find("COP (", group=group, section=sec_out))
            base["scop"] = _num(results.find("SCOP", group=group, section=sec_out))
            base["seasonal_class"] = results.find(
                "Seasonal Efficiency Class", group=group, section=sec_out
            )
        return base

    return {
        "family": family,
        "model": results.model,
        "size": size,
        "type": type_,
        "designation_code": None,
        "conditions": {"cooling": cond("Refroidissement"), "heating": cond("Chauffage")},
        "performance": {"cooling": perf("Refroidissement"), "heating": perf("Chauffage")},
        "general": {
            "refrigerant": results.find("Réfrigérant", group=cd, section=sec_out),
            "gwp": _num(results.find("GWP", group=cd, section=sec_out)),
            "supply": results.find("Alimentation", group=cd, section=sec_out),
            "max_current_A": _num(results.find("Max. courant absorbé", group=cd, section=sec_out)),
            "starting_current_A": _num(
                results.find("Courant de démarrage (LRA)", group=cd, section=sec_out)
            ),
            "sound_power_lw_dBA": _num(
                results.find("puissance acoustique Lw", group=cd, section=sec_out)
            ),
            "sound_pressure_lp_dBA": _num(
                results.find("pression acoustique Lp", group=cd, section=sec_out)
            ),
            "source_air_flow_m3h": _num(
                results.find("Source Air Volumetric Flow", group=cd, section=sec_out)
            ),
            "weight_kg": None,
        },
        "options": [],
        "warnings": [],
    }


def parse_results_html(html: str, *, model: str = "") -> GallettiResults:
    """Parse la page RisultatiCalcolo en lignes structurées (section/groupe/label/unité/valeur)."""
    rows: list[ResultRow] = []
    tbl_m = _RESULTS_TABLE_RE.search(html)
    if not tbl_m:
        return GallettiResults(model=model, rows=rows)

    section = ""
    group = ""
    for tr in _TR_RE.findall(tbl_m.group(0)):
        cells = [_clean_cell(c) for c in _CELL_RE.findall(tr)]
        cells = [c for c in cells if c]
        if not cells:
            continue
        if len(cells) == 1:
            # Ligne d'en-tête : soit une section de tête, soit un sous-groupe
            head = cells[0]
            if head in _TOP_SECTIONS:
                section = head
                group = ""
            else:
                group = head
            continue
        if len(cells) == 2:
            label, value, unit = cells[0], cells[1], ""
        else:  # 3+ : label | unité | valeur
            label, unit, value = cells[0], cells[1], cells[-1]
        rows.append(ResultRow(section=section, group=group, label=label, unit=unit, value=value))
    return GallettiResults(model=model, rows=rows)


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


@dataclass
class _HtmlForm:
    action: str
    inputs: dict[str, str]

    @property
    def has_password(self) -> bool:
        return "password" in self.inputs or any(
            k.lower() == "password" for k in self.inputs
        )


class _FormParser(HTMLParser):
    """Extrait tous les <form> d'une page : action + champs <input name=value>.

    Sert au login Keycloak (``#kc-form-login``) et à la page form_post OIDC
    (formulaire auto-soumis vers offer.gallettigroup.com).
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.forms: list[_HtmlForm] = []
        self._cur: _HtmlForm | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        ad = {k: (v or "") for k, v in attrs}
        if tag == "form":
            self._cur = _HtmlForm(action=ad.get("action", ""), inputs={})
        elif tag == "input" and self._cur is not None:
            name = ad.get("name")
            if name:
                self._cur.inputs[name] = ad.get("value", "")

    def handle_endtag(self, tag: str) -> None:
        if tag == "form" and self._cur is not None:
            self.forms.append(self._cur)
            self._cur = None


def _parse_forms(html: str) -> list[_HtmlForm]:
    parser = _FormParser()
    parser.feed(html)
    # Keycloak peut ne pas fermer <form> proprement : récupérer un form ouvert
    if parser._cur is not None:
        parser.forms.append(parser._cur)
    return parser.forms


class GallettiSelectorClient:
    """Client HTTP pour le configurateur GALLETTI (cookie ou login automatique)."""

    def __init__(self, config: GallettiConfig) -> None:
        self._config = config
        self._session: httpx.Client | None = None

    def _new_client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self._config.base_url,
            headers=self._config.headers,
            timeout=self._config.timeout_seconds,
            follow_redirects=True,
        )

    def _login(self) -> httpx.Client:
        """Se connecte via Keycloak (identifiant+mot de passe) et renvoie un client authentifié."""
        client = self._new_client()
        # 1. Page protégée -> redirige vers la page de login Keycloak
        resp = client.get("/Gestione/Offerta", params={"tipoProgetto": "1"})
        if "dtOfferte" in resp.text:
            return client  # déjà authentifié
        forms = _parse_forms(resp.text)
        login_form = next((f for f in forms if f.has_password), None)
        if login_form is None or not login_form.action:
            raise GallettiAuthError(
                "Page de login GALLETTI introuvable (flux Keycloak inattendu)."
            )
        # 2. POST identifiants
        data = dict(login_form.inputs)
        data["username"] = self._config.username
        data["password"] = self._config.password
        resp2 = client.post(login_form.action, data=data)
        # 3. Page form_post OIDC -> POST des tokens vers offer.gallettigroup.com
        post_forms = _parse_forms(resp2.text)
        if post_forms and post_forms[0].action:
            fp = post_forms[0]
            client.post(fp.action, data=fp.inputs)
        # 4. Vérifier que la session est établie
        check = client.get("/Gestione/Offerta", params={"tipoProgetto": "1"})
        if _looks_like_login(check.text):
            raise GallettiAuthError(
                "Échec du login GALLETTI : identifiant ou mot de passe incorrect ?"
            )
        return client

    def _ensure_session(self) -> httpx.Client:
        if self._session is None:
            if self._config.can_login:
                self._session = self._login()
            else:
                self._session = self._new_client()  # mode cookie
        return self._session

    def _reset_session(self) -> None:
        if self._session is not None:
            self._session.close()
        self._session = None

    def _get_html(self, path: str, params: dict[str, str] | None = None) -> str:
        if not self._config.live:
            raise GallettiAuthError(
                "GALLETTI non configuré : fournissez GALLETTI_USER + GALLETTI_PASSWORD "
                "(recommandé) ou GALLETTI_COOKIE."
            )
        html = self._get_html_once(path, params)
        if _looks_like_login(html) and self._config.can_login:
            # session expirée -> on se reconnecte une fois
            self._reset_session()
            html = self._get_html_once(path, params)
        if _looks_like_login(html):
            raise GallettiAuthError(
                f"Réponse de login reçue sur {path!r} : "
                + (
                    "échec de la reconnexion automatique (identifiants ?)."
                    if self._config.can_login
                    else "session expirée, renouvelle le cookie GALLETTI_COOKIE."
                )
            )
        return html

    def _get_html_once(self, path: str, params: dict[str, str] | None) -> str:
        client = self._ensure_session()
        try:
            resp = client.get(path, params=params)
        except httpx.HTTPError as err:
            raise GallettiError(f"Erreur réseau GALLETTI sur {path!r}: {err}") from err
        if resp.status_code in (401, 403):
            raise GallettiAuthError(f"Accès refusé ({resp.status_code}) sur {path!r}.")
        if resp.status_code >= 400:
            raise GallettiError(f"GALLETTI {resp.status_code} sur {path!r}.")
        return resp.text

    def list_projects(self, *, tipo_progetto: int = 1) -> list[GallettiProject]:
        """Liste les projets (offerte) de l'onglet Gestione/Offerta."""
        html = self._get_html("/Gestione/Offerta", params={"tipoProgetto": str(tipo_progetto)})
        return parse_projects_html(html)

    def get_project(self, project_id: int) -> GallettiProjectDetail:
        """Récupère le détail d'un projet (ses lignes d'articles)."""
        html = self._get_html(f"/Gestione/Offerta/Offerta/{project_id}")
        return parse_project_html(html, project_id=project_id)

    def get_results(
        self, *, family: str, model: str, project_id: int = 0, id_carrello: int = 0
    ) -> GallettiResults:
        """Récupère les résultats de calcul d'un modèle (conditions + performances).

        family/model forment le paramètre ``modelli`` : ``"GAL|PLE HS;PLE062HS"``.
        """
        modelli = f"{family};{model}"
        html = self._get_html(
            "/Configuratore/Wizard/RisultatiCalcolo",
            params={
                "modelli": modelli,
                "idcarrello": str(id_carrello),
                "idofferta": str(project_id),
            },
        )
        return parse_results_html(html, model=model)


def make_client_from_env() -> GallettiSelectorClient:
    """Construit un client depuis la configuration d'environnement."""
    from src.services.settings import get_settings

    settings = get_settings()
    config = GallettiConfig(
        base_url=settings.galletti_base_url or DEFAULT_BASE_URL,
        session_cookie=settings.galletti_cookie,
        username=settings.galletti_user,
        password=settings.galletti_password,
        timeout_seconds=settings.galletti_timeout_seconds,
    )
    return GallettiSelectorClient(config)
