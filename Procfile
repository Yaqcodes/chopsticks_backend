# Release runs during image build on Railway — no private Postgres DNS. DB-free only.
release: python manage.py collectstatic --noinput
# Migrations run at container start (see bin/start-web.sh) when postgres.railway.internal resolves.
web: bash bin/start-web.sh
