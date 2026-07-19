#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "=== SmartDecigen Deploy ==="

# 1. Build frontend
echo "[1/4] Building frontend..."
cd "$SCRIPT_DIR/frontend" && npx vite build --logLevel error
cd "$SCRIPT_DIR"

# 2. Commit uncommitted changes (if any)
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "[2/4] Committing changes..."
  git add -A
  git commit -m "deploy $(date '+%Y-%m-%d %H:%M')" || true
fi

# 3. Push to GitHub (API method — works on slow networks)
echo "[3/4] Pushing via GitHub API..."
if [ -z "$GH_PAT" ]; then
  if [ -f "$SCRIPT_DIR/.gh_token" ]; then
    export GH_PAT=$(cat "$SCRIPT_DIR/.gh_token")
  else
    echo "  Set GH_PAT env var or create .gh_token file with your GitHub personal access token"
    echo "  Get one at: https://github.com/settings/tokens (needs 'repo' scope)"
    exit 1
  fi
fi
python3 "$SCRIPT_DIR/push_via_api.py"

# 4. Railway will auto-deploy from GitHub
echo "[4/4] Railway auto-deploy should trigger from push"
echo "=== Done ==="
echo "URL: https://www.smartdecigen.com"
