#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════
# tunnel.sh — Ouvre un SSH tunnel vers les outils admin
#
# Usage (depuis votre poste local) :
#   bash deploy/scripts/tunnel.sh <IP_ORACLE> [USER]
#
# Puis accédez dans votre navigateur :
#   http://localhost:8080  → NocoDB     (base de données)
#   http://localhost:5678  → n8n        (automation)
#   http://localhost:8001  → Windmill   (scripts → apps)
#   http://localhost:3000  → Metabase   (analytics)
#   http://localhost:11434 → Ollama API (IA)
#
# Fermez avec Ctrl+C
# ═══════════════════════════════════════════════════════

ORACLE_IP="${1:-}"
ORACLE_USER="${2:-ubuntu}"

if [[ -z "$ORACLE_IP" ]]; then
  read -rp "IP du serveur Oracle : " ORACLE_IP
fi

echo ""
echo "════════════════════════════════════════════"
echo "  Tunnel SSH vers INVENIO admin"
echo "  Serveur : $ORACLE_USER@$ORACLE_IP"
echo "════════════════════════════════════════════"
echo ""
echo "  Accès local après connexion :"
echo "  http://localhost:8080  → NocoDB"
echo "  http://localhost:5678  → n8n"
echo "  http://localhost:8001  → Windmill"
echo "  http://localhost:3000  → Metabase"
echo ""
echo "  Fermez avec Ctrl+C"
echo "════════════════════════════════════════════"
echo ""

ssh \
  -N \
  -o ServerAliveInterval=60 \
  -o ServerAliveCountMax=3 \
  -L 8080:localhost:8080 \
  -L 5678:localhost:5678 \
  -L 8001:localhost:8001 \
  -L 3000:localhost:3000  \
  -L 11434:localhost:11434 \
  "${ORACLE_USER}@${ORACLE_IP}"
