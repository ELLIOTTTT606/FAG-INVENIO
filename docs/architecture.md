# Architecture INVENIO

Document vivant. Mis a jour a chaque sprint.

## 1. Vision

INVENIO remplace le rendu Word/PDF de GALLETTI par une chaine moderne :

1. Import d'une fiche source (DOCX ou PDF).
2. Extraction et normalisation vers un JSON canonique.
3. Selection des options et contacts (UI + Baserow).
4. Generation d'une fiche PDF au design France Air.

## 2. Composants

| Composant | Techno | Responsabilite |
|---|---|---|
| `parser` | Python, python-docx, pdfplumber | Extraction tableaux/textes, detection designation, normalisation. |
| `schema` | JSON Schema | Contrat des donnees entre parser, UI, generateur. |
| `api` | FastAPI | Endpoints upload, parse, generate, integration Baserow. |
| `services.baserow` | httpx | Lecture/ecriture Baserow (clients, options, contacts). |
| `tools.validate_csv` | Python CLI | Validation et normalisation des CSV options/accessoires. |
| `generator` | Playwright (a venir) | HTML + CSS -> PDF avec sommaire cliquable. |
| `ui` | React + Vite (a venir) | Pages Home, Import, Contacts, Options, Generation. |

## 3. Schema canonique (resume)

Le contrat principal est `src/schema/pac_geg_schema.json`. Champs cles :

- `family` : `PAC` ou `GEG`.
- `model`, `size`, `type` : identifiants machine.
- `designation_code` : chaine brute reconnue dans le DOCX.
- `conditions.cooling` / `conditions.heating` : T eau / air, charge, glycol.
- `performance.cooling_power_kW` / `performance.heating_power_kW`.
- `hydraulics`, `electrical`, `acoustics`.
- `options[]`, `contacts.*`.

Toutes les valeurs numeriques sont arrondies a 1 decimale (sauf `_percent`
qui sont des entiers). Les valeurs absentes sont `null` (UI affiche
"Donnee non disponible").

## 4. Tables Baserow

| Table | ID | Usage |
|---|---|---|
| CLIENTS | 939119 | Clients existants + nouveaux clients. |
| Contacts FORCE DE VENTE | 939355 | TCI / TCS par departement. |
| Contacts SOLUTION | 939361 | Contacts Solution Habitat. |
| OPTIONS et ACCESSOIRES | 941070 | Catalogue d'options par modele/taille. |
| PRIX MACHINES | 939101 | (Future) prix par configuration. |

Authentification via `Authorization: Token <BASEROW_TOKEN>`. Token stocke
dans Vault, expose au backend via la variable d'environnement
`BASEROW_TOKEN`. Rotation prevue tous les 90 jours.

## 5. Roadmap

| Sprint | Duree | Livrables |
|---|---|---|
| **0** (en cours) | 2-3 j | Bootstrap repo, CI, JSON Schema, `validate_csv.py`, parser DOCX MVP. |
| 1 | 3-5 j | Parser DOCX complet + parser PDF natif, mapping etoffe, tests d'integration. |
| 2 | 4-6 j | Generateur HTML -> PDF (Playwright), endpoint `/generate`, frontend minimal upload + preview. |
| 3 | 2-4 j | Integration Baserow live, ecriture nouveaux clients, S3/MinIO pour plans, OCR optionnel. |

## 6. Securite

- Aucun secret dans le repo (`.env` est gitignore).
- Tokens Baserow / S3 lus depuis l'environnement, geres via Vault en prod.
- Validation stricte des uploads (taille max, types MIME : `.docx`, `.pdf`).
- Sanitization du nom de fichier avant stockage.

## 7. Deploiement (cible)

- Image Docker Python 3.11 + Playwright Chromium.
- CI : GitHub Actions (lint, typecheck, tests, security scan).
- CD : a definir avec l'equipe Ops (registry + cluster cible).

## 8. Decisions techniques (ADR resumes)

| Decision | Choix | Raison |
|---|---|---|
| Framework API | FastAPI | Validation Pydantic, OpenAPI auto, async natif. |
| Parser PDF | pdfplumber | Texte + tableaux, dependance pure Python (pas de Ghostscript). |
| Generation PDF | Playwright | Fidelite CSS / fonts / SVG superieure aux alternatives. |
| Fuzzy matching | rapidfuzz | Performant, API simple. |
| JSON validation | jsonschema | Standard, deja utilise pour l'OpenAPI. |
