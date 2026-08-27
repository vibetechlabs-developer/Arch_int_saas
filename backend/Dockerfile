# syntax=docker/dockerfile:1
#
# Multi-stage build for the INT Projects SaaS backend (BE-020).
# Stages: base -> dev (local development) / builder -> production
# (runtime image, no build toolchain, non-root user).
#
# Same image is used for all three app-tier compose services (django,
# celery-worker, celery-beat) — only the `command:` differs per service in
# docker-compose.yml, so application code never drifts between them.

# --- base: shared OS deps for every later stage ----------------------------
FROM python:3.12-slim AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev gcc curl \
    && rm -rf /var/lib/apt/lists/*

# --- dev: hot-reload target, dev dependencies included ----------------------
FROM base AS dev
COPY requirements/dev.txt requirements/base.txt ./requirements/
RUN pip install --no-cache-dir -r requirements/dev.txt
COPY . .
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# --- builder: production dependencies only, isolated from the runtime image -
FROM base AS builder
COPY requirements/prod.txt requirements/base.txt ./requirements/
RUN pip install --no-cache-dir -r requirements/prod.txt

# --- production: slim runtime, no build tools, non-root user ---------------
FROM python:3.12-slim AS production
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home appuser
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . .
# collectstatic runs while still root, before the ownership handoff below —
# STATIC_ROOT must be writable at the point it runs.
RUN python manage.py collectstatic --noinput \
    && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
