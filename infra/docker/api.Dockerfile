# FLOODTAIL API — production image
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin appuser

COPY requirements.txt pyproject.toml ./
COPY apps ./apps
COPY packages ./packages
COPY Nairobi_Data ./Nairobi_Data

# Model artifacts are gitignored — mount ./models at runtime (see docker-compose.prod.yml).
RUN mkdir -p /app/models /app/data \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -e . \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/v1/health || exit 1

# Single worker by default (ML + long runs). Override UVICORN_WORKERS in compose if needed.
CMD ["sh", "-c", "uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --workers ${UVICORN_WORKERS:-1} --proxy-headers --forwarded-allow-ips '*'"]
