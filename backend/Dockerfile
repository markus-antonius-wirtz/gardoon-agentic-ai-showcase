# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app
COPY pyproject.toml ./
RUN uv sync --no-dev --no-install-project

COPY app ./app
RUN uv sync --no-dev

FROM python:3.12-slim-bookworm AS runtime

RUN groupadd --gid 10001 gardoon && \
    useradd --uid 10001 --gid gardoon --shell /bin/false --create-home gardoon

WORKDIR /app
COPY --from=builder --chown=gardoon:gardoon /app/.venv /app/.venv
COPY --from=builder --chown=gardoon:gardoon /app/app /app/app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER gardoon
EXPOSE 8000

HEALTHCHECK --interval=20s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
