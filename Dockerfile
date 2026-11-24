FROM python:3.12-slim AS base

COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY --chmod=755 docker-entrypoint.sh /usr/local/bin/
ENTRYPOINT ["docker-entrypoint.sh"]


# Local development. docker-compose mounts the code into /app.
FROM base AS dev

COPY pyproject.toml uv.lock /app/
RUN uv sync --locked --no-install-project

CMD ["rundev"]


FROM base AS prod

COPY pyproject.toml uv.lock /app/
RUN uv sync --locked --no-install-project --no-dev

COPY . /app/

RUN mkdir -p logs mediafiles \
    && SECRET_KEY=collectstatic python manage.py collectstatic --noinput

RUN useradd --system --no-create-home app \
    && chown -R app logs mediafiles
USER app

EXPOSE 8000
CMD ["runprod"]
