"""Tests du client GALLETTI (parsing de la liste des projets)."""

from __future__ import annotations

from src.services.galletti_client import (
    GallettiAuthError,
    GallettiConfig,
    GallettiSelectorClient,
    parse_project_html,
    parse_projects_html,
    parse_results_html,
    results_to_canonical,
)

# Fixture synthétique reproduisant la structure de la table #dtOfferte
# (colonnes : Statut, N° projet, Date, Client, Nom, Utilisateur, Prix, Actions).
_SAMPLE_HTML = """
<html><body>
<table class="table" id="dtOfferte">
  <thead><tr>
    <th>Statut</th><th>Numéro projet</th><th>Date</th><th>Client</th>
    <th>Nom du Projet</th><th>Utilisateur</th><th>Total Prix</th><th>Actions</th>
  </tr></thead>
  <tbody>
    <tr>
      <td>Brouillon</td><td>26.000001.A</td><td>01/01/2026</td><td></td>
      <td>Projet Alpha</td><td>Jean Test</td><td>10.000,00 €</td>
      <td><div class="btn-group"><ul class="dropdown-menu">
        <li><a href="javascript:void(0);" onclick="readOnlyOfferta(111);">Visualiser</a></li>
      </ul></div></td>
    </tr>
    <tr>
      <td>Finalisation</td><td>26.000002.B</td><td>02/02/2026</td><td></td>
      <td>Projet Beta</td><td>Marie Test</td><td>25.500,00 €</td>
      <td><div class="btn-group"><ul class="dropdown-menu">
        <li><a href="javascript:void(0);" onclick="readOnlyOfferta(222);">Visualiser</a></li>
      </ul></div></td>
    </tr>
  </tbody>
</table>
</body></html>
"""


def test_parse_projects_html_extracts_rows() -> None:
    projects = parse_projects_html(_SAMPLE_HTML)
    assert len(projects) == 2

    first = projects[0]
    assert first.id == 111
    assert first.numero == "26.000001.A"
    assert first.date == "01/01/2026"
    assert first.nom == "Projet Alpha"
    assert first.utilisateur == "Jean Test"
    assert first.prix_total == "10.000,00 €"

    second = projects[1]
    assert second.id == 222
    assert second.nom == "Projet Beta"
    assert second.prix_total == "25.500,00 €"


def test_parse_projects_ignores_rows_without_id() -> None:
    html = """
    <table id="dtOfferte"><tbody>
      <tr><td>x</td><td>26.0</td><td>d</td><td></td><td>No id</td><td>u</td><td>0 €</td><td></td></tr>
    </tbody></table>
    """
    assert parse_projects_html(html) == []


def test_parse_projects_to_dict_roundtrip() -> None:
    projects = parse_projects_html(_SAMPLE_HTML)
    d = projects[0].to_dict()
    assert d["id"] == 111
    assert d["nom"] == "Projet Alpha"


def test_config_live_flag() -> None:
    assert GallettiConfig(session_cookie="").live is False
    assert GallettiConfig(session_cookie="sid=abc").live is True


def test_config_headers_include_cookie() -> None:
    cfg = GallettiConfig(session_cookie="sid=abc")
    assert cfg.headers["Cookie"] == "sid=abc"
    assert "Cookie" not in GallettiConfig().headers


def test_list_projects_without_cookie_raises_auth() -> None:
    client = GallettiSelectorClient(GallettiConfig(session_cookie=""))
    try:
        client.list_projects()
    except GallettiAuthError:
        return
    raise AssertionError("GallettiAuthError attendu sans cookie de session")


# Fixture reproduisant le JSON.parse('[{...}]') embarqué dans la page détail.
_PROJECT_HTML = r"""
<html><body>
<script>
var offerta = JSON.parse('[{"IdFamiglia":"GAL|PLE HS","ArticoloModello":"PLE062HS","ArticoloDescrizioneTradotta":"Groupe eau glacee","PrezzoScontato":26515.00,"ListaOpzioniConfigurazione":"10001,10068,10000","Posizione":1},{"IdFamiglia":"GAL|MLI","ArticoloModello":"MLI030H0","ArticoloDescrizioneTradotta":"","PrezzoScontato":10261.00,"ListaOpzioniConfigurazione":"","Posizione":2}]');
</script>
</body></html>
"""


def test_parse_project_html_extracts_articles() -> None:
    detail = parse_project_html(_PROJECT_HTML, project_id=42)
    assert detail.id == 42
    assert len(detail.articles) == 2

    first = detail.articles[0]
    assert first.position == 1
    assert first.model == "PLE062HS"
    assert first.family == "GAL|PLE HS"
    assert first.description == "Groupe eau glacee"
    assert first.price == 26515.00
    assert first.option_codes == ["10001", "10068", "10000"]
    assert first.is_machine is True

    second = detail.articles[1]
    assert second.model == "MLI030H0"
    assert second.option_codes == []


def test_parse_project_html_no_articles() -> None:
    detail = parse_project_html("<html><body>rien</body></html>", project_id=7)
    assert detail.id == 7
    assert detail.articles == []
    assert detail.machines == []


def test_get_project_without_cookie_raises_auth() -> None:
    client = GallettiSelectorClient(GallettiConfig(session_cookie=""))
    try:
        client.get_project(123)
    except GallettiAuthError:
        return
    raise AssertionError("GallettiAuthError attendu sans cookie de session")


# Fixture reproduisant la table #dtParametriCalcolo (avec &nbsp; comme en vrai).
_RESULTS_HTML = """
<table id="dtParametriCalcolo">
  <tr><td>Données d'Entrée</td></tr>
  <tr><td>Refroidissement&nbsp;</td></tr>
  <tr><td>Temp. entrée eau utilisation</td><td>°C</td><td>&nbsp; 12.0</td></tr>
  <tr><td>Temp. sortie eau utilisation</td><td>°C</td><td>&nbsp; 7.0</td></tr>
  <tr><td>Pourcentage de Charge</td><td>%</td><td>&nbsp; 100</td></tr>
  <tr><td>Chauffage&nbsp;</td></tr>
  <tr><td>Temp. entrée eau utilisation</td><td>°C</td><td>&nbsp; 40.0</td></tr>
  <tr><td>Données pour calcul selon la norme UNI EN 14511&nbsp;</td></tr>
  <tr><td>Calculs selon la norme UNI EN 14511</td><td>&nbsp; Oui</td></tr>
  <tr><td>Données de Sortie</td></tr>
  <tr><td>Refroidissement&nbsp;</td></tr>
  <tr><td>Puissance de refroidissement (*)</td><td>kW</td><td>&nbsp; 55.0</td></tr>
  <tr><td>Débit d'eau du circuit utilisateur (*)</td><td>l/h</td><td>&nbsp; 9446</td></tr>
  <tr><td>EER (*)</td><td>W/W</td><td>&nbsp; 2.60</td></tr>
  <tr><td>Chauffage&nbsp;</td></tr>
  <tr><td>Puissance de chauffage (*)</td><td>kW</td><td>&nbsp; 48.6</td></tr>
  <tr><td>COP (*)</td><td>W/W</td><td>&nbsp; 2.21</td></tr>
  <tr><td>Common Data&nbsp;</td></tr>
  <tr><td>Niveau de puissance acoustique Lw (unité de base) [sans options] (**)</td><td>dB(A)</td><td>&nbsp; 81</td></tr>
  <tr><td>Réfrigérant</td><td>&nbsp; R454B</td></tr>
  <tr><td>GWP</td><td>&nbsp; 466</td></tr>
</table>
"""


def test_parse_results_extracts_rows_with_sections() -> None:
    res = parse_results_html(_RESULTS_HTML, model="PLE062HS")
    assert res.model == "PLE062HS"
    # La valeur froid est bien scopée à sa section/groupe (pas confondue avec chaud)
    assert res.find("entrée eau", group="Refroidissement", section="Données d'Entrée") == "12.0"
    assert res.find("Puissance de refroidissement", section="Données de Sortie") == "55.0"


def test_results_to_canonical_maps_key_figures() -> None:
    res = parse_results_html(_RESULTS_HTML, model="PLE062HS")
    canon = results_to_canonical(res, family="GAL|PLE HS")

    assert canon["model"] == "PLE062HS"
    assert canon["family"] == "GAL|PLE HS"

    perf = canon["performance"]
    assert perf["cooling"]["power_kW"] == 55.0
    assert perf["cooling"]["eer"] == 2.60
    assert perf["cooling"]["water_flow_lph"] == 9446.0
    assert perf["heating"]["power_kW"] == 48.6
    assert perf["heating"]["cop"] == 2.21

    assert canon["general"]["sound_power_lw_dBA"] == 81.0
    assert canon["general"]["refrigerant"] == "R454B"
    assert canon["general"]["gwp"] == 466.0


def test_parse_results_empty_without_table() -> None:
    res = parse_results_html("<html>pas de table</html>", model="X")
    assert res.rows == []
    assert res.find("quoi que ce soit") is None
