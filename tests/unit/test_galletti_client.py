"""Tests du client GALLETTI (parsing de la liste des projets)."""

from __future__ import annotations

from src.services.galletti_client import (
    GallettiAuthError,
    GallettiConfig,
    GallettiSelectorClient,
    parse_projects_html,
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
