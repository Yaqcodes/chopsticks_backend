# Release runs during image build — no DB. collectstatic only.
release: python manage.py collectstatic --noinput
# Migrations run in railway.toml preDeployCommand before healthcheck; web starts gunicorn only.
web: gunicorn chopsticks_backend.wsgi --bind 0.0.0.0:$PORT --workers 3 --threads 2 --timeout 60 --access-logfile - --error-logfile -
