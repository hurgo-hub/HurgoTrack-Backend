"""Celery de hurgotrack.

Reutiliza la app Celery del motor (``enginedj.celery.app``) y fija el
settings por defecto antes de importarla. Al importarse desde
``config/__init__.py``, Django y el worker comparten la misma app, así que
``shared_task(...).delay()`` usa el broker configurado en settings.

Worker y beat:

    celery -A config worker -l info
    celery -A config beat -l info
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from enginedj.celery import app  # noqa: E402

__all__ = ("app",)
