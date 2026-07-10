#!/usr/bin/env bash
set -e

echo "=== SmartDecision Local Setup ==="

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "Error: Docker is required. Install at https://docker.com"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "Warning: Node.js not found. Frontend will not start."; }

# Check for GEMINI_API_KEY
if [ -z "$GEMINI_API_KEY" ]; then
  if [ -f backend/.env ]; then
    source backend/.env 2>/dev/null || true
  fi
  if [ -z "$GEMINI_API_KEY" ]; then
    echo "Error: GEMINI_API_KEY is not set."
    echo "  Get a free key at https://aistudio.google.com/apikey"
    echo "  Then: echo 'GEMINI_API_KEY=your-key' > backend/.env"
    exit 1
  fi
fi

export GEMINI_API_KEY

echo ""
echo "1. Starting MongoDB + Backend API via Docker..."
echo "   Backend will be at http://localhost:8000"
echo ""

docker compose up --build -d

echo ""
echo "2. Waiting for backend to be ready..."
for i in {1..30}; do
  if curl -s http://localhost:8000/api/ >/dev/null 2>&1; then
    echo "   Backend is ready!"
    break
  fi
  sleep 2
done

if command -v node >/dev/null 2>&1; then
  echo ""
  echo "3. Starting frontend dev server..."
  echo "   Frontend will be at http://localhost:3000"
  echo ""
  cd frontend && npm start
else
  echo ""
  echo "Frontend not started. Run manually:"
  echo "  cd frontend && npm start"
  echo ""
  echo "Or open the API directly at http://localhost:8000/docs"
fi
