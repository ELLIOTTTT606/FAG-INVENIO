#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# INVENIO — Script d'installation automatique
# Oracle Cloud Always Free · Ubuntu 22.04 ARM64
#
# Usage (sur le VPS Oracle, après SSH) :
#   bash install.sh
#
# Ce script fait tout :
#   1. Installe Docker + Docker Compose
#   2. Clone le dépôt INVENIO
#   3. Configure l'environnement (.env)
#   4. Lance tous les services
#   5. Télécharge le modèle IA Ollama
#   6. Configure les sauvegardes automatiques
#   7. Affiche le résumé d'accès
# ═══════════════════════════════════════════════════════════════

set -euo pipefail
IFS=$'\n\t'

# ── Couleurs ──────────────────────────────────────────────────
RED='\033[0;31m';   GREEN='\033[0;32m';  YELLOW='\033[1;33m'
BLUE='\033[0;34m';  CYAN='\033[0;36m';   BOLD='\033[1m';  NC='\033[0m'

log()     { echo -e "${CYAN}[INVENIO]${NC} $1"; }
success() { echo -e "${GREEN}[✓]${NC} $1"; }
warn()    { echo -e "${YELLOW}[!]${NC} $1"; }
error()   { echo -e "${RED}[✗]${NC} $1"; exit 1; }
title()   { echo -e "\n${BOLD}${BLUE}── $1 ──${NC}\n"; }
sep()     { echo -e "${BLUE}────────────────────────────────────────${NC}"; }

# ── Bannière ──────────────────────────────────────────────────
clear
echo -e "${BOLD}${CYAN}"
cat << 'BANNER'
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║        I N V E N I O   —   France Air                     ║
║        Déploiement automatique · €0/mois                  ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
BANNER
echo -e "${NC}"

# ── Variables de configuration ────────────────────────────────
REPO_URL="${REPO_URL:-}"          # URL Git (demandée si vide)
INSTALL_DIR="${INSTALL_DIR:-/opt/invenio}"
OLLAMA_MODEL="${OLLAMA_MODEL:-mistral}"

# ── Vérifications préliminaires ───────────────────────────────
title "Vérifications"

# OS check
if ! grep -q "Ubuntu\|Debian" /etc/os-release 2>/dev/null; then
  warn "Ce script est optimisé pour Ubuntu/Debian. Continuez à vos risques."
fi

# User check
if [[ $EUID -ne 0 ]]; then
  error "Lancez ce script avec sudo : sudo bash install.sh"
fi

success "Système compatible"

# ── Étape 1 : Docker ─────────────────────────────────────────
title "Étape 1/7 — Installation de Docker"

if command -v docker &>/dev/null; then
  success "Docker déjà installé ($(docker --version | cut -d' ' -f3 | tr -d ','))"
else
  log "Installation de Docker..."
  apt-get update -qq
  apt-get install -y -qq ca-certificates curl gnupg lsb-release
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu \
    $(lsb_release -cs) stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
  systemctl enable --now docker
  success "Docker installé"
fi

# Ajouter l'utilisateur sudo au groupe docker
SUDO_USER="${SUDO_USER:-ubuntu}"
if id "$SUDO_USER" &>/dev/null; then
  usermod -aG docker "$SUDO_USER" 2>/dev/null || true
fi

# ── Étape 2 : Cloner le dépôt ────────────────────────────────
title "Étape 2/7 — Récupération du code INVENIO"

if [[ -z "$REPO_URL" ]]; then
  read -rp "$(echo -e "${CYAN}URL du dépôt Git INVENIO${NC} (ex: git@github.com:france-air/fag-invenio.git) : ")" REPO_URL
fi

if [[ -d "$INSTALL_DIR/.git" ]]; then
  log "Dépôt déjà présent — mise à jour..."
  git -C "$INSTALL_DIR" pull --ff-only
  success "Code mis à jour"
else
  log "Clonage dans $INSTALL_DIR..."
  git clone "$REPO_URL" "$INSTALL_DIR"
  success "Code cloné"
fi

cd "$INSTALL_DIR"

# ── Étape 3 : Configuration ───────────────────────────────────
title "Étape 3/7 — Configuration de l'environnement"

if [[ -f "deploy/.env" ]]; then
  warn "Fichier .env existant détecté — conservation des valeurs actuelles."
  warn "Supprimez deploy/.env et relancez pour reconfigurer."
else
  log "Configuration interactive..."
  sep

  echo -e "\n${BOLD}Domaine & SSL (DuckDNS)${NC}"
  echo -e "  → Créez un sous-domaine gratuit sur ${CYAN}https://www.duckdns.org${NC}"
  read -rp "  Votre domaine DuckDNS (ex: invenio-fa.duckdns.org) : " ENV_DOMAIN
  read -rp "  Token DuckDNS (visible sur duckdns.org) : " ENV_DUCK_TOKEN

  echo -e "\n${BOLD}Mot de passe base de données${NC}"
  read -rsp "  Choisissez un mot de passe fort (min 20 caractères) : " ENV_DB_PASS
  echo

  echo -e "\n${BOLD}Baserow (pendant la transition vers NocoDB)${NC}"
  echo -e "  → Laissez vide pour ignorer (le mock Baserow sera utilisé)"
  read -rp "  Token Baserow (optionnel) : " ENV_BASEROW_TOKEN

  # Générer une clé secrète
  SECRET=$(openssl rand -hex 32)

  # Créer le .env
  cp deploy/.env.example deploy/.env
  sed -i "s|DOMAIN=.*|DOMAIN=$ENV_DOMAIN|"                         deploy/.env
  sed -i "s|DUCKDNS_TOKEN=.*|DUCKDNS_TOKEN=$ENV_DUCK_TOKEN|"       deploy/.env
  sed -i "s|DB_PASSWORD=.*|DB_PASSWORD=$ENV_DB_PASS|"              deploy/.env
  sed -i "s|SECRET_KEY=.*|SECRET_KEY=$SECRET|"                     deploy/.env
  sed -i "s|BASEROW_TOKEN=.*|BASEROW_TOKEN=$ENV_BASEROW_TOKEN|"    deploy/.env

  chmod 600 deploy/.env
  success "Fichier deploy/.env créé"
fi

# ── Étape 4 : Firewall Oracle Cloud ──────────────────────────
title "Étape 4/7 — Firewall du serveur"

# iptables sur Ubuntu 22.04 par défaut bloque tout.
# Oracle Cloud ajoute aussi ses propres Security Lists — à configurer manuellement.
if command -v ufw &>/dev/null; then
  ufw --force enable
  ufw allow 22/tcp   comment "SSH"
  ufw allow 80/tcp   comment "HTTP (redirect vers HTTPS)"
  ufw allow 443/tcp  comment "HTTPS"
  ufw allow 443/udp  comment "HTTP/3"
  # Tous les autres ports restent fermés (accès via SSH tunnel uniquement)
  success "UFW configuré (80, 443 ouverts ; admin via SSH tunnel uniquement)"
else
  warn "UFW non disponible — vérifiez que les ports 80/443 sont ouverts dans Oracle Security Lists"
fi

echo -e "\n${YELLOW}Action manuelle requise dans Oracle Cloud Console :${NC}"
echo    "  Networking → Virtual Cloud Networks → Security Lists"
echo    "  → Ajouter Ingress Rules pour : TCP port 80 et TCP/UDP port 443"
read -rp "  Appuyez sur Entrée une fois configuré..."

# ── Étape 5 : Lancer les services ────────────────────────────
title "Étape 5/7 — Démarrage de la stack"

log "Construction de l'image INVENIO (peut prendre 3-5 minutes)..."
docker compose -f deploy/docker-compose.yml --env-file deploy/.env build --no-cache

log "Démarrage de tous les services..."
docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d

log "Attente que PostgreSQL soit prêt..."
RETRIES=30
until docker compose -f deploy/docker-compose.yml exec -T postgres \
      pg_isready -U "${DB_USER:-invenio}" &>/dev/null || [ "$RETRIES" -eq 0 ]; do
  sleep 2; RETRIES=$((RETRIES - 1))
  echo -n "."
done
echo
[ "$RETRIES" -eq 0 ] && error "PostgreSQL n'a pas démarré dans les temps."
success "PostgreSQL prêt"

log "Attente que NocoDB soit prêt..."
sleep 20   # NocoDB prend un peu de temps au premier démarrage
success "Services démarrés"

# ── Étape 6 : Modèle IA Ollama ────────────────────────────────
title "Étape 6/7 — Téléchargement du modèle IA ($OLLAMA_MODEL)"

log "Téléchargement de $OLLAMA_MODEL (~4 GB — peut prendre 5-10 minutes)..."
docker compose -f deploy/docker-compose.yml exec -T ollama \
  ollama pull "$OLLAMA_MODEL" && success "Modèle $OLLAMA_MODEL téléchargé" \
  || warn "Échec du téléchargement — relancez avec : ./scripts/pull-model.sh $OLLAMA_MODEL"

# ── Étape 7 : DuckDNS auto-renouvellement ────────────────────
title "Étape 7/7 — Maintenance automatique"

# Créer le script de renouvellement DuckDNS
cat > /opt/invenio/deploy/scripts/duckdns.sh << 'DUCKDNS'
#!/bin/bash
# Renouvellement automatique de l'IP DuckDNS
source /opt/invenio/deploy/.env
CURRENT_IP=$(curl -fsSL https://api.ipify.org 2>/dev/null)
curl -fsSL "https://www.duckdns.org/update?domains=${DOMAIN%.duckdns.org}&token=${DUCKDNS_TOKEN}&ip=${CURRENT_IP}" \
  >> /var/log/duckdns.log 2>&1
DUCKDNS
chmod +x /opt/invenio/deploy/scripts/duckdns.sh

# Créer le script de backup NocoDB
cat > /opt/invenio/deploy/scripts/backup.sh << 'BACKUP'
#!/bin/bash
# Backup quotidien de PostgreSQL
source /opt/invenio/deploy/.env
BACKUP_DIR="/opt/invenio/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

# Dump PostgreSQL complet
docker compose -f /opt/invenio/deploy/docker-compose.yml exec -T postgres \
  pg_dumpall -U "${DB_USER:-invenio}" \
  | gzip > "$BACKUP_DIR/dump_$DATE.sql.gz"

# Garder seulement les 30 derniers backups
ls -t "$BACKUP_DIR"/*.sql.gz | tail -n +31 | xargs rm -f 2>/dev/null || true

echo "[$(date)] Backup OK : dump_$DATE.sql.gz" >> /var/log/invenio-backup.log
BACKUP
chmod +x /opt/invenio/deploy/scripts/backup.sh

# Crontab
(crontab -l 2>/dev/null || true; cat << 'CRON'
# INVENIO — DuckDNS renouvellement (toutes les 5 minutes)
*/5 * * * * /opt/invenio/deploy/scripts/duckdns.sh >> /var/log/duckdns.log 2>&1
# INVENIO — Backup quotidien à 3h du matin
0 3 * * * /opt/invenio/deploy/scripts/backup.sh >> /var/log/invenio-backup.log 2>&1
CRON
) | crontab -

success "Tâches automatiques configurées (DuckDNS + backup quotidien)"

# ── Résumé final ─────────────────────────────────────────────
sep; sep
DOMAIN_VAL=$(grep "^DOMAIN=" deploy/.env | cut -d= -f2)
PUBLIC_IP=$(curl -fsSL https://api.ipify.org 2>/dev/null || echo "<IP_ORACLE>")

echo -e "\n${BOLD}${GREEN}✓ INVENIO déployé avec succès !${NC}\n"

echo -e "${BOLD}Accès public :${NC}"
echo -e "  🌐 Application INVENIO : ${CYAN}https://$DOMAIN_VAL${NC}"
echo -e "  ⚠  Le SSL peut prendre 2-3 minutes (Let's Encrypt)"

echo -e "\n${BOLD}Accès outils d'administration (via SSH tunnel) :${NC}"
echo -e "  Lancez d'abord : ${CYAN}bash deploy/scripts/tunnel.sh${NC}"
echo -e "  Puis ouvrez dans votre navigateur :"
echo -e "  🗄  NocoDB    → ${CYAN}http://localhost:8080${NC}  (base de données)"
echo -e "  ⚡  n8n       → ${CYAN}http://localhost:5678${NC}  (automation)"
echo -e "  🔧 Windmill  → ${CYAN}http://localhost:8001${NC}  (scripts → apps)"
echo -e "  📊 Metabase  → ${CYAN}http://localhost:3000${NC}  (analytics)"

echo -e "\n${BOLD}Commandes utiles :${NC}"
echo -e "  Voir les logs :    ${CYAN}docker compose -f deploy/docker-compose.yml logs -f${NC}"
echo -e "  Statut services :  ${CYAN}docker compose -f deploy/docker-compose.yml ps${NC}"
echo -e "  Mettre à jour :    ${CYAN}bash deploy/scripts/update.sh${NC}"
echo -e "  Accès admin :      ${CYAN}bash deploy/scripts/tunnel.sh${NC}"

echo -e "\n${BOLD}IP du serveur :${NC} $PUBLIC_IP"
echo -e "${YELLOW}→ Ajoutez cette IP dans Oracle Cloud Security Lists si ce n'est pas fait.${NC}"

sep; sep
echo ""
