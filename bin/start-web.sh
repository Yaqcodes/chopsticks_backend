#!/usr/bin/env bash
# Run migrations at container start (private Postgres DNS is available here).
# Do NOT run migrate in the Procfile release phase — Railway often executes release
# during the image build, where postgres.railway.internal does not resolve.
set -euo pipefail
cd "$(dirname "$0")/.."
python manage.py migrate --noinput
exec gunicorn chopsticks_backend.wsgi \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers 3 \
  --threads 2 \
  --timeout 60 \
  --access-logfile - \
  --error-logfile -
