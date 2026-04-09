# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.13.3

FROM python:${PYTHON_VERSION}-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install uv binary (dependency manager used by this project).
COPY --from=ghcr.io/astral-sh/uv:0.8.15 /uv /uvx /bin/

WORKDIR /app

# Copy lockfiles first to maximize Docker layer cache.
COPY pyproject.toml uv.lock ./

# Install runtime dependencies into /app/.venv (reproducible with uv.lock).
RUN uv sync --frozen --no-dev --no-install-project \
    && /app/.venv/bin/python -c "import uvicorn"


FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOST=0.0.0.0 \
    APP_PORT=10461 \
    APP_DEBUG=false \
    HOME=/home/app \
    XDG_CONFIG_HOME=/home/app/.config \
    XDG_CACHE_HOME=/home/app/.cache \
    MPLCONFIGDIR=/home/app/.config/matplotlib \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Run as non-root user in container.
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs npm \
    chromium \
    fonts-noto-cjk \
    fonts-wqy-zenhei \
    && npm install -g @mermaid-js/mermaid-cli \
    && fc-cache -f \
    && apt-get clean && rm -rf /var/lib/apt/lists/* \
    && addgroup --system app \
    && adduser --system --home /home/app --ingroup app app \
    && mkdir -p /home/app/.config/matplotlib \
    && mkdir -p /home/app/.cache/dconf \
    && chown -R app:app /home/app

# Copy prebuilt virtualenv and app source.
COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app app ./app
COPY --chown=app:app main.py ./main.py

EXPOSE 10461

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os, urllib.request; port=os.getenv('APP_PORT', '10461'); urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=3)" || exit 1

USER app

CMD ["/app/.venv/bin/python", "main.py"]
