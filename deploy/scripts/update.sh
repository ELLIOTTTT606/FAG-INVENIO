#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════
# update.sh — Mise à jour de la stack INVENIO
#
# Usage (sur le serveur Oracle) :
#   bash deploy/scripts/update.sh
#
# Ce script :
#   1. Pull le nouveau code Git
#   2. Rebuild l'image INVENIO
#   3. Redémarre les services sans downtime
#   4. Vérifie la santé de l'application
# ═══════════════════════════════════════════════════════

set -euo pipefail

INSTALL_DIR="/opt/invenio"
COMPOSE="docker compose -f $INSTALL_DIR/deploy/docker-compose.yml --env-file $INSTALL_DIR/deploy/.env"

GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
log() { echo -e "${CYAN}[UPDATE]${NC} $1"; }
ok()  { echo -e "${GREEN}[✓]${NC} $1"; }

cd "$INSTALL_DIR"

log "1/4 — Pull du code..."
git pull --ff-only
ok "Code mis à jour"

log "2/4 — Rebuild de l'image INVENIO..."
$COMPOSE build invenio
ok "Image reconstruite"

log "3/4 — Redémarrage des services (zero-downtime)..."
$COMPOSE up -d --no-deps invenio
ok "Services redémarrés"

log "4/4 — Vérification santé..."
sleep 5
if $COMPOSE exec -T invenio \
     python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" &>/dev/null; then
  ok "INVENIO répond correctement"
else
  echo -e "\033[0;31m[!]\033[0m INVENIO ne répond pas — vérifiez les logs :"
  echo "    $COMPOSE logs -f invenio"
  exit 1
fi

echo ""
ok "Mise à jour terminée !"
