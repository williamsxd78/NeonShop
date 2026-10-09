#!/usr/bin/env bash
# NeonKeys Market: one-command VPS installer (Ubuntu/Debian). Usage: sudo ./install.sh
set -euo pipefail
cd "$(dirname "$0")"
ROOT=$(pwd)
ENVF="$ROOT/deploy/.env"
DC="docker compose -f $ROOT/deploy/docker-compose.yml"
DATA="$ROOT/deploy/initial-data/neonkeys-data.archive.gz"

[ "$(id -u)" -eq 0 ] || { echo "Please run as root: sudo ./install.sh"; exit 1; }

echo "==> Checking Docker"
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi
docker compose version >/dev/null 2>&1 || { apt-get update -y && apt-get install -y docker-compose-plugin; }
systemctl enable --now docker >/dev/null 2>&1 || true

if ! grep -q avx /proc/cpuinfo 2>/dev/null; then MONGO_IMAGE=mongo:4.4; else MONGO_IMAGE=mongo:7; fi

if [ ! -f "$ENVF" ]; then
  echo "==> First-time setup"
  read -rp "Domain pointing to this server (e.g. market.example.com). Leave blank to use the IP over http: " DOMAIN
  read -rp "Admin email [admin@market.com]: " ADMIN_EMAIL
  ADMIN_EMAIL=${ADMIN_EMAIL:-admin@market.com}
  while :; do
    read -rsp "Admin password (min 8 chars, no single quotes): " ADMIN_PASSWORD; echo
    [[ ${#ADMIN_PASSWORD} -ge 8 && "$ADMIN_PASSWORD" != *"'"* ]] && break
    echo "  Password too short or contains a single quote."
  done
  read -rp "Resend API key for emails (blank = emails off): " RESEND_API_KEY
  EMAIL_PROVIDER=none; EMAIL_FROM=""
  if [ -n "$RESEND_API_KEY" ]; then
    EMAIL_PROVIDER=resend
    read -rp "Sender (domain verified in Resend), e.g. NeonKeys <no-reply@${DOMAIN:-yourdomain.com}>: " EMAIL_FROM
  fi
  SEED_DEMO=false
  if [ ! -f "$DATA" ]; then
    read -rp "Create demo accounts + sample products? [y/N]: " D; [[ "$D" =~ ^[Yy]$ ]] && SEED_DEMO=true
  fi
  if [ -n "$DOMAIN" ]; then SITE_ADDRESS=$DOMAIN; SITE_URL="https://$DOMAIN"; else SITE_ADDRESS=":80"; SITE_URL="http://$(curl -s4 ifconfig.me || hostname -I | awk '{print $1}')"; fi
  cat > "$ENVF" <<EOF
SITE_ADDRESS=$SITE_ADDRESS
CORS_ORIGINS=$SITE_URL
DB_NAME=neonkeys
APP_NAME=neonkeys
JWT_SECRET=$(openssl rand -hex 32)
ADMIN_EMAIL=$ADMIN_EMAIL
ADMIN_PASSWORD='$ADMIN_PASSWORD'
EMAIL_PROVIDER=$EMAIL_PROVIDER
RESEND_API_KEY=$RESEND_API_KEY
EMAIL_FROM='$EMAIL_FROM'
EMAIL_FROM_NAME='NeonKeys Market'
EMAIL_REPLY_TO=
SEED_DEMO=$SEED_DEMO
MONGO_IMAGE=$MONGO_IMAGE
EOF
  chmod 600 "$ENVF"
  echo "  Saved settings to deploy/.env"
fi

set -a; . "$ENVF"; set +a
mkdir -p "$ROOT/deploy/data/uploads"

echo "==> Starting database"
$DC up -d mongo
for i in $(seq 1 60); do
  $DC exec -T mongo sh -c "mongosh --quiet --eval 1 || mongo --quiet --eval 1" >/dev/null 2>&1 && break; sleep 2
done

USERS=$($DC exec -T mongo sh -c "mongosh --quiet --eval \"db.getSiblingDB('$DB_NAME').users.countDocuments()\" 2>/dev/null || mongo --quiet --eval \"db.getSiblingDB('$DB_NAME').users.count()\"" | tr -dc '0-9')
if [ -f "$DATA" ] && [ "${USERS:-0}" = "0" ]; then
  read -rp "Import the bundled data (products, settings, banners, accounts) from the preview site? [Y/n]: " IMP
  if [[ ! "$IMP" =~ ^[Nn]$ ]]; then
    SRC_DB=$(cat "$ROOT/deploy/initial-data/SOURCE_DB")
    echo "==> Importing bundled data"
    $DC exec -T mongo mongorestore --quiet --archive --gzip --nsFrom "$SRC_DB.*" --nsTo "$DB_NAME.*" < "$DATA"
    if [ -d "$ROOT/deploy/initial-data/uploads" ]; then cp -rn "$ROOT/deploy/initial-data/uploads/." "$ROOT/deploy/data/uploads/"; fi
    if [ "$(echo "$ADMIN_EMAIL" | tr 'A-Z' 'a-z')" != "admin@market.com" ]; then
      $DC exec -T mongo sh -c "mongosh --quiet --eval \"db.getSiblingDB('$DB_NAME').users.updateOne({email:'admin@market.com'},{\\\$set:{status:'suspended',role:'buyer'}})\" 2>/dev/null || true" >/dev/null
    fi
  fi
fi

echo "==> Building and starting the app (first build takes a few minutes)"
$DC up -d --build

echo
echo "============================================================"
echo " NeonKeys Market is running."
if [ "$SITE_ADDRESS" = ":80" ]; then echo " Open: http://$(hostname -I | awk '{print $1}')"; else echo " Open: https://$SITE_ADDRESS  (HTTPS certificate is issued automatically)"; fi
echo " Admin login: $ADMIN_EMAIL  (password you entered)"
echo " Update later:  sudo ./deploy/update.sh"
echo " Backup:        sudo ./deploy/backup.sh"
echo "============================================================"
