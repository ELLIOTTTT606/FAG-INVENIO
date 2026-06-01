# INVENIO — Instructions pour Claude Code

## Mission

Exécute le script `setup_invenio.py` pour configurer automatiquement
le projet INVENIO. Ce script fait tout :

1. Crée tous les répertoires manquants
2. Écrit tous les fichiers frontend (React/TypeScript) et deploy
3. Copie les PNG des pages de garde dans `ui/public/covers/`
4. Applique les correctifs de code nécessaires
5. Configure les permissions des scripts shell

## Prérequis

- Python 3.8 ou supérieur (déjà installé)
- Le script doit être lancé depuis la **racine du projet**
- Les fichiers PNG (.png) doivent être à la racine du projet

## Commande unique à exécuter

```bash
python setup_invenio.py
```

## Après l'installation — tester en local

```bash
cd ui
npm install
npm run dev
```

Ouvrir http://localhost:5173 dans le navigateur.

## En cas d'erreur npm

Si `npm run dev` retourne des erreurs TypeScript, lancer :

```bash
cd ui
npm run typecheck
```

Et corriger les imports manquants signalés.

## Structure créée par le script

```
projet/
├── Dockerfile
├── deploy/
│   ├── .env.example
│   ├── Caddyfile
│   ├── docker-compose.yml
│   ├── install.sh
│   ├── postgres-init/01-init.sql
│   └── scripts/
│       ├── install.sh
│       ├── migrate_baserow_to_nocodb.py
│       ├── tunnel.sh
│       └── update.sh
├── src/
│   ├── api/_static.py
│   └── services/nocodb_client.py
└── ui/
    ├── public/covers/     ← tous les PNG
    └── src/
        ├── App.tsx
        ├── api/client.ts
        ├── components/
        │   ├── layout/AnimatedBackground.tsx
        │   └── layout/Navigation.tsx
        │   └── ui/atoms.tsx
        ├── lib/
        │   ├── machines.ts
        │   ├── sessionContext.ts
        │   └── theme.tsx
        └── pages/
            ├── Contacts.tsx
            ├── Generate.tsx
            ├── Home.tsx
            ├── Machine.tsx
            ├── Options.tsx
            └── Projet.tsx
```
