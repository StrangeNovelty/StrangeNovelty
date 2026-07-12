FROM ghcr.io/astral-sh/uv:0.11.28 AS uv

FROM python:3.14.6-slim-bookworm AS build
COPY --from=uv /uv /bin/uv
RUN apt-get update \
    && apt-get install --yes --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock README.md ./
COPY manage.py ./
COPY src ./src
COPY templates ./templates
COPY docs/operations ./docs/operations
RUN uv sync --frozen --no-default-groups --group production \
    && .venv/bin/python manage.py collectstatic --noinput \
       --settings=strange_novelty.settings.build

FROM python:3.14.6-slim-bookworm AS runtime
RUN apt-get update \
    && apt-get install --yes --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home --shell /usr/sbin/nologin app
WORKDIR /app
COPY --from=build --chown=app:app /app /app
COPY --chown=app:app scripts ./scripts
ENV PATH="/app/.venv/bin:${PATH}" \
    DJANGO_SETTINGS_MODULE=strange_novelty.settings.production \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
USER 10001:10001
EXPOSE 8000
CMD ["/app/scripts/start-web.sh"]
