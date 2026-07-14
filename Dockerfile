FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ .
RUN npx vite build

FROM python:3.11-slim
WORKDIR /app
# Force clean rebuild — Stage 1 trust rails deployed 2026-07-13
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends build-essential gcc g++ && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --timeout=120 -r requirements.txt
COPY backend/ .
COPY --from=frontend-builder /app/frontend/build /frontend/build
EXPOSE 8000
CMD uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}
