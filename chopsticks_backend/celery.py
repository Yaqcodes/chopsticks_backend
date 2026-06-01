import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chopsticks_backend.settings')

app = Celery('chopsticks_backend')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
