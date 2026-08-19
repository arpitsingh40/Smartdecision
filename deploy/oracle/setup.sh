#!/usr/bin/env bash
# Oracle Always Free bootstrap — installs Docker, Caddy and deploys Smartdecision.
# Usage (on a fresh Ubuntu 22.04/24.04 Ampere A1 VM):
#   sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/arpitsingh40/Smartdecision/main/deploy/oracle/setup.sh)" -- smartdecigen.com
set -euo pipefail

DOMAIN="${1:-smartdecigen.com}"
APP_DIR=/opt/smartdecision
REPO_URL="https://github.com/arpitsingh40/Smartdecision.git"
BRANCH="main"

log() { echo "==> $*"; }

# ---- 1. System packages: git, curl, firewall tooling ----
log "[1/8] Installing system packages"
sudo apt-get update -qq
sudo apt-get install -y -qq ca-certificates curl git ufw

# ---- 2. Docker Engine (official installer — works on ARM64) ----
log "[2/8] Installing Docker"
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sudo sh
fi
sudo usermod -aG docker "$USER"

# ---- 3. Caddy (official repo) — free auto-HTTPS reverse proxy ----
log "[3/8] Installing Caddy"
if ! command -v caddy >/dev/null 2>&1; then
  sudo apt-get install -y -qq debian-keyring debian-archive-keyring apt-transport-https
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
  sudo apt-get update -qq
  sudo apt-get install -y -qq caddy
fi

# ---- 4. Firewall: SSH + HTTP/HTTPS only ----
log "[4/8] Configuring firewall"
sudo ufw allow OpenSSH >/dev/null 2>&1 || sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable >/dev/null 2>&1

# ---- 5. Fetch the code (idempotent clone + pull) ----
log "[5/8] Fetching source"
sudo mkdir -p "$APP_DIR"
if [ ! -d "$APP_DIR/.git" ]; then
  sudo git clone -b "$BRANCH" "$REPO_URL" "$APP_DIR"
else
  sudo git -C "$APP_DIR" fetch --quiet origin
  sudo git -C "$APP_DIR" reset --hard --quiet "origin/$BRANCH"
fi

# ---- 6. Environment file — auto-generate JWT secret, prompt for the rest ----
log "[6/8] Creating .env"
if [ ! -f "$APP_DIR/.env" ]; then
  sudo cp "$APP_DIR/deploy/oracle/.env.example" "$APP_DIR/.env"
  sudo sed -i "s/^JWT_SECRET=.*/JWT_SECRET=$(openssl rand -hex 32)/" "$APP_DIR/.env"
  sudo sed -i "s|^FRONTEND_BASE_URL=.*|FRONTEND_BASE_URL=https://$DOMAIN|" "$APP_DIR/.env"
fi
if grep -q "^MONGO_URL=$" "$APP_DIR/.env"; then
  echo "NOTE: edit $APP_DIR/.env and set MONGO_URL (MongoDB Atlas) and DEEPSEEK_API_KEY,"
  echo "      then run: sudo bash $APP_DIR/deploy/oracle/update.sh"
fi

# ---- 7. Caddy reverse proxy (domain -> 127.0.0.1:8000, auto TLS) ----
log "[7/8] Configuring Caddy for $DOMAIN"
sudo sed "s/__DOMAIN__/$DOMAIN/g" "$APP_DIR/deploy/oracle/Caddyfile" | sudo tee /etc/caddy/Caddyfile >/dev/null
sudo systemctl enable --now caddy >/dev/null 2>&1 || true
sudo systemctl reload caddy 2>/dev/null || true

# ---- 8. Build and start the app (single container serves API + frontend) ----
log "[8/8] Building and starting Smartdecision"
sudo docker compose -f "$APP_DIR/docker-compose.yml" --env-file "$APP_DIR/.env" up -d --build

sleep 8
if curl -fsS "http://127.0.0.1:8000/api/health" >/dev/null 2>&1; then
  log "Backend is UP. Live at https://$DOMAIN (once DNS points here)"
else
  log "Backend starting... check: sudo docker compose -f $APP_DIR/docker-compose.yml logs -f"
fi
log "Next: point an A record for $DOMAIN (and www) to this VM's public IP."
log "      Edit secrets in $APP_DIR/.env, then run update.sh to apply."