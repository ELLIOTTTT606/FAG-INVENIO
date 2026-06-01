#!/usr/bin/env python3
"""
deploy/scripts/migrate_baserow_to_nocodb.py
────────────────────────────────────────────
Migre les 5 tables Baserow vers NocoDB en une commande.

Usage :
    # Depuis le répertoire racine du projet INVENIO
    python deploy/scripts/migrate_baserow_to_nocodb.py

Variables d'environnement requises (dans deploy/.env) :
    BASEROW_URL, BASEROW_TOKEN
    NOCODB_URL, NOCODB_TOKEN
    BASEROW_TABLE_* → IDs sources
    NOCODB_TABLE_*  → IDs cibles (créés manuellement dans NocoDB d'abord)

Ordre d'exécution :
    1. Créez les tables dans NocoDB (même structure que Baserow)
    2. Notez les IDs NocoDB (md_xxx) dans deploy/.env
    3. Lancez ce script
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv("deploy/.env")

# ── Configuration ────────────────────────────────────────────────
BASEROW_URL   = os.environ["BASEROW_URL"]
BASEROW_TOKEN = os.environ["BASEROW_TOKEN"]

NOCODB_URL   = os.environ["NOCODB_URL"]
NOCODB_TOKEN = os.environ["NOCODB_TOKEN"]

TABLES: list[dict[str, str]] = [
    {
        "name": "CLIENTS",
        "baserow_id": os.environ.get("BASEROW_TABLE_CLIENTS", "939119"),
        "nocodb_id":  os.environ.get("NOCODB_TABLE_CLIENTS", ""),
    },
    {
        "name": "Contacts FORCE DE VENTE",
        "baserow_id": os.environ.get("BASEROW_TABLE_CONTACTS_FORCE_VENTE", "939355"),
        "nocodb_id":  os.environ.get("NOCODB_TABLE_CONTACTS_FORCE_VENTE", ""),
    },
    {
        "name": "Contacts SOLUTION",
        "baserow_id": os.environ.get("BASEROW_TABLE_CONTACTS_SOLUTION", "939361"),
        "nocodb_id":  os.environ.get("NOCODB_TABLE_CONTACTS_SOLUTION", ""),
    },
    {
        "name": "OPTIONS et ACCESSOIRES",
        "baserow_id": os.environ.get("BASEROW_TABLE_OPTIONS_ACCESSOIRES", "941070"),
        "nocodb_id":  os.environ.get("NOCODB_TABLE_OPTIONS_ACCESSOIRES", ""),
    },
    {
        "name": "PRIX MACHINES",
        "baserow_id": os.environ.get("BASEROW_TABLE_PRIX_MACHINES", "939101"),
        "nocodb_id":  os.environ.get("NOCODB_TABLE_PRIX_MACHINES", ""),
    },
]

BATCH_SIZE = 50   # Lignes par appel NocoDB


def _baserow_headers() -> dict[str, str]:
    return {"Authorization": f"Token {BASEROW_TOKEN}"}


def _nocodb_headers() -> dict[str, str]:
    return {"xc-token": NOCODB_TOKEN, "Content-Type": "application/json"}


def fetch_all_baserow(table_id: str) -> list[dict[str, Any]]:
    """Récupère toutes les lignes de la table Baserow (pagination automatique)."""
    rows: list[dict[str, Any]] = []
    url = f"{BASEROW_URL}/api/database/rows/table/{table_id}/?size=200"
    with httpx.Client(timeout=60) as client:
        while url:
            resp = client.get(url, headers=_baserow_headers())
            resp.raise_for_status()
            data = resp.json()
            rows.extend(data.get("results", []))
            url = data.get("next")
            print(f"  Récupérées {len(rows)} lignes...", end="\r")
    print(f"  ✓ {len(rows)} lignes récupérées depuis Baserow        ")
    return rows


def clean_row(row: dict[str, Any]) -> dict[str, Any]:
    """Nettoie une ligne Baserow pour l'import dans NocoDB (retire les champs Baserow-spécifiques)."""
    return {
        k: v for k, v in row.items()
        if not k.startswith("_") and k not in ("id", "order")
    }


def push_to_nocodb(table_id: str, rows: list[dict[str, Any]]) -> int:
    """Envoie les lignes vers NocoDB par batch. Retourne le nombre de lignes créées."""
    if not rows:
        return 0
    created = 0
    with httpx.Client(base_url=NOCODB_URL, timeout=60) as client:
        for i in range(0, len(rows), BATCH_SIZE):
            chunk = [clean_row(r) for r in rows[i : i + BATCH_SIZE]]
            resp = client.post(
                f"/api/v2/tables/{table_id}/records",
                headers=_nocodb_headers(),
                json=chunk,
            )
            if resp.is_error:
                print(f"\n  [!] Erreur batch {i}-{i+BATCH_SIZE}: {resp.status_code} {resp.text[:200]}")
                continue
            data = resp.json()
            batch_count = len(data) if isinstance(data, list) else 1
            created += batch_count
            print(f"  Importées {created}/{len(rows)} lignes...", end="\r")
            time.sleep(0.1)   # Respecter le rate limit NocoDB
    print(f"  ✓ {created}/{len(rows)} lignes importées dans NocoDB        ")
    return created


def migrate_table(table: dict[str, str]) -> bool:
    """Migre une table. Retourne True si succès."""
    name = table["name"]
    baserow_id = table["baserow_id"]
    nocodb_id = table["nocodb_id"]

    print(f"\n{'─'*50}")
    print(f"Table : {name}")
    print(f"  Baserow ID : {baserow_id}")
    print(f"  NocoDB ID  : {nocodb_id or '⚠ NON CONFIGURÉ'}")

    if not nocodb_id:
        print(f"  [SKIP] NOCODB_TABLE_{name.upper().replace(' ', '_')} non défini dans .env")
        return False

    try:
        rows = fetch_all_baserow(baserow_id)
        if not rows:
            print("  [INFO] Table vide — rien à migrer")
            return True
        push_to_nocodb(nocodb_id, rows)
        return True
    except Exception as exc:
        print(f"  [ERREUR] {exc}")
        return False


def main() -> None:
    print("═" * 50)
    print("  MIGRATION BASEROW → NOCODB")
    print("═" * 50)

    # Vérifications
    missing_nocodb = [t["name"] for t in TABLES if not t["nocodb_id"]]
    if missing_nocodb:
        print(f"\n⚠ Tables NocoDB non configurées dans .env :")
        for name in missing_nocodb:
            print(f"   - {name}")
        print("\n→ Créez ces tables dans NocoDB (http://localhost:8080 via SSH tunnel)")
        print("  puis ajoutez leurs IDs (md_xxx) dans deploy/.env")
        print("  Format : NOCODB_TABLE_CLIENTS=md_xxxxxxxxxxxxxxxx")

    # Migration
    results: dict[str, bool] = {}
    for table in TABLES:
        results[table["name"]] = migrate_table(table)

    # Résumé
    print(f"\n{'═'*50}")
    print("  RÉSUMÉ DE MIGRATION")
    print(f"{'═'*50}")
    ok_count = sum(results.values())
    for name, success in results.items():
        icon = "✓" if success else "✗"
        print(f"  {icon} {name}")
    print(f"\n  {ok_count}/{len(TABLES)} tables migrées avec succès")

    if ok_count == len(TABLES):
        print("\n  ✓ Migration complète !")
        print("  Mettez à jour deploy/.env :")
        print("    - Remplissez NOCODB_TOKEN")
        print("    - Commentez les variables BASEROW_*")
    else:
        print("\n  ⚠ Certaines tables n'ont pas été migrées — vérifiez les erreurs ci-dessus")
        sys.exit(1)


if __name__ == "__main__":
    main()
