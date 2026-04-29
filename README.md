# INVENIO

SaaS interne **France Air - Solution Habitat** pour remplacer le rendu Word/PDF
produit par GALLETTI : import d'une fiche source (.docx / .pdf), extraction
et normalisation des donnees, selection des contacts et options, puis
generation d'une fiche de selection PDF au design France Air.

> **Statut** : MVP en cours - Sprint 0 (bootstrap, validation CSV, schema
> JSON canonique, parser DOCX minimal). Voir `docs/architecture.md` pour la
> roadmap complete.

---

## Sommaire

- [Architecture](#architecture)
- [Prerequis](#prerequis)
- [Installation](#installation)
- [Lancement](#lancement)
- [Outils CLI](#outils-cli)
- [Tests](#tests)
- [Structure du depot](#structure-du-depot)
- [Conventions](#conventions)
- [Securite et secrets](#securite-et-secrets)

---

## Architecture

Pipeline cible :

```
fichier source (.docx / .pdf)
        |
        v
   [ parser ]  ----> JSON canonique (valide contre pac_geg_schema.json)
        |
        v
   [ UI / API ]  <-> Baserow (clients, options, contacts)
        |
        v
   [ generator HTML -> PDF ] (Playwright)
        |
        v
   fiche de selection PDF (design France Air)
```

Modules livres dans ce sprint :

- `src/parser/docx_parser.py` - parser DOCX MVP (tableaux + designation).
- `src/schema/pac_geg_schema.json` - schema canonique (PAC / GEG).
- `src/schema/options_schema.json` - schema des CSV options/accessoires.
- `tools/validate_csv.py` - validation et normalisation des CSV options.
- `src/api/main.py` - squelette FastAPI (health + upload + parse).
- `src/services/baserow_client.py` - wrapper minimal Baserow.

## Prerequis

- Python 3.11 ou plus.
- Node.js 22+ pour le frontend `ui/`.
- (Optionnel) Playwright + Chromium pour la generation PDF (a installer
  separement : `pip install -e ".[pdf]" && playwright install chromium`).

## Installation

```bash
# Cloner et se placer sur la branche de developpement
git clone <repo-url>
cd FAG-INVENIO
git checkout claude/galletti-to-invenio-migration-zrKBt

# Environnement Python
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"

# Variables d'environnement
cp .env.example .env
# editer .env (en particulier BASEROW_TOKEN si vous voulez l'API live)
```

## Lancement

API FastAPI (dev) :

```bash
uvicorn src.api.main:app --reload --port 8000
# -> http://localhost:8000/health
# -> http://localhost:8000/docs (OpenAPI)
```

Frontend React (dev) :

```bash
cd ui
npm install
npm run dev
# -> http://localhost:5173
# Le serveur Vite proxifie /parse et /health vers http://localhost:8000.
```

Les pages livrees a ce stade :

- `/` — Home, CTA "Generer ma fiche".
- `/import` — dropzone .docx / .pdf, appel `/parse/{docx,pdf}`, resume des
  champs extraits avec icones ✓ / ⚠, options decodees, alertes warnings.
- `/contacts` — recherche client (autocomplete debouncee), picker
  departement (recherche + groupage par region), contacts TCI / TCS /
  Solution Habitat charges depuis `/contacts/department/{dep}`.

Le backend utilise un `MockContactsRepository` quand `BASEROW_TOKEN`
n'est pas defini (donnees factices mais plausibles), et bascule sur
`BaserowContactsRepository` lorsque le token et l'URL sont presents.

## Outils CLI

### Validation d'un CSV options/accessoires

```bash
python -m tools.validate_csv \
    --input examples/options_accessoires_sample.csv \
    --schema src/schema/options_schema.json \
    --out-valid validated/options_accessoires_sample.valid.csv \
    --out-report reports/options_accessoires_sample.report.json
```

Le script :

1. verifie la presence des colonnes obligatoires,
2. valide chaque ligne contre le JSON Schema,
3. normalise (`code` en majuscules, `available` en booleen, espaces),
4. detecte les doublons sur la cle `(model, size, option_code)`,
5. ecrit le CSV nettoye et un rapport JSON detaille.

Code retour : `0` si pas d'erreur (warnings autorises), `1` sinon.

### Parsing DOCX (preview)

```bash
python -m src.parser.docx_parser examples/sample_galletti.docx
```

Affiche le JSON canonique partiel extrait du fichier.

### Parsing PDF (preview)

```bash
python -m src.parser.pdf_parser examples/sample_galletti.pdf
```

### Synchronisation du decodeur de designation depuis Baserow

La chaine de designation GALLETTI (`PLP052HS2B A000CE000I00110 0000000I000000000000`)
encode les options par position. Pour les decoder, le parser lit
`src/parser/designation_decoder.csv`. Ce CSV est genere a partir d'une
table Baserow contenant les regles `(family, block, position, character)
-> option metadata`:

```bash
export BASEROW_URL=https://api.baserow.io
export BASEROW_TOKEN=...
python -m tools.baserow_to_decoder \
    --table-id 941070 \
    --output src/parser/designation_decoder.csv \
    --field-map family=Famille block=Bloc position=Position \
                character=Caractere code=Code category=Categorie \
                label_fr=Libelle description_fr=Description tips_fr=Tips
```

Tant que le CSV est vide, chaque caractere non-zero produit une entree
placeholder dans `options[]` et un warning `designation_decoder_missing`.

## Tests

Backend Python :

```bash
pytest                         # tous les tests
pytest tests/unit -q           # uniquement les tests unitaires
pytest --cov=src --cov=tools   # avec couverture
ruff check .                   # lint
mypy src tools                 # typecheck
```

Frontend React :

```bash
cd ui
npm run typecheck              # tsc --noEmit
npm run lint                   # eslint
npm test                       # vitest run
npm run build                  # build production
```

## Structure du depot

```
FAG-INVENIO/
|- .github/
|  |- workflows/ci.yml
|  `- pull_request_template.md
|- docs/
|  `- architecture.md
|- src/
|  |- api/                      # FastAPI app
|  |- parser/                   # docx_parser.py + mapping
|  |- schema/                   # JSON Schemas
|  `- services/                 # baserow_client.py
|- tools/
|  `- validate_csv.py
|- tests/
|  |- unit/
|  |- integration/
|  `- fixtures/
|- examples/
|- ui/
|  |- src/
|  |  |- pages/                 # Home.tsx, Import.tsx
|  |  |- components/             # Dropzone, ExtractionSummary
|  |  |- api/                    # client + types
|  |  |- styles/                 # tokens (Tailwind)
|  |  `- test/                   # vitest tests + fixtures
|  |- index.html
|  |- vite.config.ts
|  |- tailwind.config.ts
|  `- package.json
|- pyproject.toml
|- .env.example
|- .gitignore
`- README.md
```

## Conventions

- **Branches** : `claude/<sujet>-<hash>` pour les iterations IA.
- **Commits** : style imperatif, scope explicite (`parser:`, `tools:`,
  `schema:`, `api:`, `docs:`, `ci:`).
- **PR** : draft par defaut, description avec checklist, lier les issues.
- **Lint / type** : `ruff` + `mypy` doivent passer en CI.
- **Couverture** : objectif >= 80 % sur `src/` et `tools/`.

## Securite et secrets

- Aucun secret dans le repo : utiliser `.env` (gitignore) ou un Vault.
- Le token Baserow est lu via `BASEROW_TOKEN` dans l'environnement.
- Rotation prevue tous les 90 jours (voir `docs/architecture.md`).
