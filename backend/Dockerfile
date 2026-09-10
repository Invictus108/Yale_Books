# syntax=docker/dockerfile:1
#
# For Coolify with Base Directory = backend, so the build context is backend/.
# The frontend CANNOT be built here: frontend/ lives outside this context. It
# ships as the pre-built static/ directory committed to the repo.
#
#   Regenerate before deploying frontend changes:
#     cd frontend && npm run build:backend

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.cache/huggingface \
    FRONTEND_DIST=/app/static

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Bake the embedding model in so the first request does not stall on a cold
# download. Needs ~1GB of build RAM; drop this line if the build host is small
# and accept a slow (or failing) first embedding request instead.
RUN python -c "from embeddings import get_model; get_model()"

# CAS is unavailable, so the NetID demo login is the default for this
# deployment. Set DEMO_LOGIN=false in Coolify once CAS works again.
ENV DEMO_LOGIN=true

ENV PORT=3000
EXPOSE 3000

# sh -c so ${PORT} expands; exec so gunicorn is PID 1 and gets SIGTERM cleanly.
CMD ["sh", "-c", "exec gunicorn app:app --bind 0.0.0.0:${PORT:-3000} --workers 1 --threads 2 --timeout 180"]
