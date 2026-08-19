#!/usr/bin/env bash
# Update an existing Oracle deployment — pull latest code, rebuild, reload Caddy.
set -euo pipefail

APP_DIR=/opt/smartdecision

log() { echo "==> $*"; }

log "Pulling latest code"
sudo git -C "$APP_DIR" fetch --quiet origin
sudo git -C "$APP_DIR" reset --hard --quiet origin/main

log "Rebuilding and restarting containers"
sudo docker compose -f "$APP_DIR/docker-compose.yml" --env-file "$APP_DIR/.env" up -d --build

log "Reloading Caddy"
sudo systemctl reload caddy 2>/dev/null || true

log "Done. Health check: curl -fsS http://127.0.0.1:8000/api/health"