# syntax=docker/dockerfile:1.7
# Imagen del backend de Hurgo Track (daphne, worker y beat usan la misma).
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production

WORKDIR /app

# El core (EngineDj vH0.1.1) llega ya armado en vendor/: lo pone deploy/deploy.sh
# desde tu PC, así el servidor no necesita acceso a GitHub. Se instala por ruta
# de archivo para que pip nunca lo busque en PyPI. Si el .whl cambia (moviste la
# etiqueta), Docker vuelve a instalarlo.
COPY requirements.txt .
COPY vendor/ vendor/
RUN set -e; \
    whl="$(ls vendor/enginedj-*.whl)"; \
    pip install "${whl}[postgres]"; \
    grep -v -i -E '^[[:space:]]*enginedj' requirements.txt > /tmp/requirements.txt; \
    pip install -r /tmp/requirements.txt; \
    rm /tmp/requirements.txt

RUN useradd --create-home --uid 1000 app \
    && mkdir -p /app/staticfiles /app/media \
    && chown -R app:app /app

COPY --chown=app:app . .
RUN chmod +x deploy/entrypoint.sh

USER app
EXPOSE 8000

ENTRYPOINT ["/app/deploy/entrypoint.sh"]
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "--proxy-headers", "enginedj.asgi:application"]
