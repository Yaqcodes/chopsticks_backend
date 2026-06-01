from .celery import app as celery_app

# Celery CLI (`celery -A chopsticks_backend`) looks up `app` on the package.
app = celery_app

__all__ = ('celery_app', 'app')
