# ===== Stage 1: Build frontend =====
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json ./
RUN npm install --legacy-peer-deps
COPY frontend/ .
COPY frontend/.env.production ./
RUN npx craco build

# ===== Stage 2: Build backend =====
FROM python:3.11-slim
WORKDIR /app

RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \
    build-essential gcc g++ && \
    rm -rf /var/lib/apt/lists/*

# Backend dependencies
COPY backend/requirements.txt backend/
RUN pip install --no-cache-dir --timeout=120 -r backend/requirements.txt

# Backend code — into backend/ subdir to match Railway's custom start command
COPY backend/ backend/

# Frontend build from stage 1 — placed at /app/frontend/build/ as server.py expects
COPY --from=frontend-builder /app/frontend/build frontend/build

EXPOSE 8000