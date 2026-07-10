# ===== Stage 1: Build frontend =====
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --legacy-peer-deps
COPY frontend/ .
RUN npx craco build

# ===== Stage 2: Build backend =====
FROM python:3.11-slim
WORKDIR /app

# Backend dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Backend code
COPY backend/ .

# Frontend build from stage 1 — placed at /frontend/build/ as server.py expects
COPY --from=frontend-builder /app/frontend/build /frontend/build

EXPOSE 8000

CMD uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}