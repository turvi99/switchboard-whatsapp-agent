# syntax=docker/dockerfile:1
#
# Single production Dockerfile (Task 6) that packages both the backend and
# the built frontend into one image, suitable for GCP Cloud Run (or any
# single-container host). Build from the repo root:
#
#   docker build -t switchboard .
#   docker run -p 8080:8080 --env-file .env switchboard
#
# ---------------------------------------------------------------------------
# Stage 1 - build the React dashboard
# ---------------------------------------------------------------------------
FROM node:20-slim AS frontend-builder
WORKDIR /build/frontend

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --no-audit --no-fund

COPY frontend/ ./
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2 - Python runtime serving the API + the built dashboard
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app

# Built dashboard lands at /app/static, which app/main.py auto-mounts at "/"
# the moment it sees the directory exists (see app/main.py's static block).
COPY --from=frontend-builder /build/frontend/dist ./static

# Cloud Run injects $PORT and expects the container to honour it; 8080 is
# the conventional default for local `docker run`.
ENV PORT=8080
EXPOSE 8080

# Minimal unprivileged runtime user.
RUN useradd --create-home --uid 10001 appuser
USER appuser

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
