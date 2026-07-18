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
GH_URL=$(git remote get-url gh-token 2>/dev/null)
if [ -n "$GH_URL" ]; then
  export GH_PAT=$(echo "$GH_URL" | sed 's|https://[^:]*:\([^@]*\)@.*|\1|')
  python3 "$SCRIPT_DIR/push_via_api.py"
else
  echo "  No gh-token remote configured"
fi

# 4. Railway will auto-deploy from GitHub
echo "[4/4] Railway auto-deploy should trigger from push"
echo "=== Done ==="
echo "URL: https://www.smartdecigen.com"
