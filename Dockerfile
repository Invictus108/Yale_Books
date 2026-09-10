# syntax=docker/dockerfile:1

# ---------- stage 1: build the React app ----------
FROM node:20-alpine AS frontend
WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


# ---------- stage 2: python runtime that serves API + build ----------
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.cache/huggingface \
    FRONTEND_DIST=/app/frontend/dist

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY --from=frontend /app/frontend/dist frontend/dist

# Bake the embedding model into the image so the first request does not stall
# on a cold download. Remove this line to trade image size for slower first use.
RUN python -c "import sys; sys.path.insert(0, 'backend'); from embeddings import get_model; get_model()"

ENV PORT=3000
EXPOSE 3000

# sh -c so ${PORT} expands; exec so gunicorn is PID 1 and gets SIGTERM cleanly.
CMD ["sh", "-c", "exec gunicorn --chdir backend app:app --bind 0.0.0.0:${PORT:-3000} --workers 1 --threads 2 --timeout 180"]
