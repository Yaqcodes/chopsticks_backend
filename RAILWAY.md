# Deploying Chopsticks Backend on Railway

Single Django service serving all tenants (Chopsticks & Bowls, Roschi Water, Zmall) backed by Railway Postgres and a Railway S3-compatible Storage Bucket. All hostnames are driven by `BASE_URL`, so the same code/branch ships locally (SQLite + disk) and in production (Postgres + bucket) with zero edits.

> Legacy PythonAnywhere notes still live in [PYTHONANYWHERE.md](./PYTHONANYWHERE.md). Decommission once Railway is verified.

---

## 1. Provision services in Railway

In the Railway project, create three services:

1. **Django service** - this repo, branch `railway`. Procfile + `runtime.txt` are detected by Nixpacks automatically.
2. **PostgreSQL** plugin.
3. **Bucket** (Storage Bucket, S3-compatible).

Then **link** the database and bucket to the Django service:

- Postgres -> Connect: injects private `DATABASE_URL` (`${{Postgres.DATABASE_URL}}`) and public `DATABASE_PUBLIC_URL` (`${{Postgres.DATABASE_PUBLIC_URL}}`). **Do not run `migrate` during image build** — private DNS (`postgres.railway.internal`) is unavailable there.
- Bucket -> Connect: choose the Django service. Railway injects `BUCKET`, `ACCESS_KEY_ID`, `SECRET_ACCESS_KEY`, `ENDPOINT`, `REGION`. Settings auto-detect them and switch the storage backend.

---

## 2. Set environment variables

Copy values from [`.env.railway.template`](./.env.railway.template) into the Django service's **Variables** tab. Critical ones:

| Variable | Source | Notes |
|---|---|---|
| `SECRET_KEY` | generate fresh | never reuse the dev key |
| `DEBUG` | `False` | hard requirement in prod |
| `BASE_URL` | Railway public URL (or custom domain later) | drives OAuth, Paystack, absolute media URLs |
| `ALLOWED_HOSTS` | hostnames you serve | comma-separated |
| `CORS_ALLOWED_ORIGINS` | tenant frontends | scheme-included |
| `CSRF_TRUSTED_ORIGINS` | optional | `BASE_URL` is auto-added |
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` | private host; used at **container start** |
| `DATABASE_PUBLIC_URL` | `${{Postgres.DATABASE_PUBLIC_URL}}` | optional; for `manage.py migrate` from your laptop |
| `BUCKET` / `ACCESS_KEY_ID` / `SECRET_ACCESS_KEY` / `ENDPOINT` / `REGION` | Bucket link | Railway-injected |

When the Railway public URL is not yet known (first deploy), set `BASE_URL` to a placeholder, deploy, copy the assigned `*.up.railway.app` URL, then update `BASE_URL` and redeploy. After cutover to a custom domain (e.g. `https://api.zmall.ng`), only `BASE_URL` and `ALLOWED_HOSTS` need to change in Railway plus the OAuth/Paystack dashboards. No code change.

---

## 3. Deploy

The Procfile separates **build** (no database) from **runtime** (migrations):

```
release: python manage.py collectstatic --noinput
web:     bash bin/start-web.sh   # migrate, then gunicorn
```

Railway often runs `release` while **building the image**, where `postgres.railway.internal` does not resolve. Migrations therefore run in `bin/start-web.sh` when the container starts (private `DATABASE_URL` works).

The healthcheck path is `/healthz/` (configured in `railway.toml`).

### `could not translate host name "postgres.railway.internal"`

| Symptom | Fix |
|--------|-----|
| Fails during **build** with `migrate` in the log | Expected before this branch — deploy latest `railway` (migrate moved to `start-web.sh`). |
| Only `DATABASE_URL` is set | Add `${{Postgres.DATABASE_URL}}` via **Connect** (not a hand-copied URL). |
| `migrate` from your machine | Set `DATABASE_PUBLIC_URL=${{Postgres.DATABASE_PUBLIC_URL}}` locally or export `USE_DATABASE_PUBLIC_URL=1`. |

---

## 4. Storage model

- **Phase 1 (default):** Railway Buckets are private. The API serializers return absolute URLs through `core.media_urls.absolute_media_url`, which calls `default_storage.url(key)` to generate **presigned GET URLs** (default TTL 7 days, configurable via `AWS_QUERYSTRING_EXPIRE`). The frontend already accepts absolute URLs.
- **Phase 2 (later):** when a CDN (or public-bucket origin) sits in front of the bucket, set `MEDIA_CDN_BASE_URL=https://cdn.zmall.ng` and toggle `AWS_QUERYSTRING_AUTH=False`. Stored object keys (`menu_items/...`, `categories/...`, etc.) stay the same; only URL construction changes. **No DB migration, no code change.**

Object keys are tenant-agnostic by prefix today (`menu_items/`, `categories/`, `products/`, `spotlights/`, `avatars/`). Per-tenant key prefixing can be added later without breaking existing rows.

---

## 5. Data migration (one-time)

From the legacy environment to Railway:

1. **Database**: dump from current source (`pg_dump` if Postgres; `python manage.py dumpdata` for SQLite source) and load into the new Postgres. Verify with `python manage.py showmigrations` then `migrate --check`.
2. **Media**: bulk-copy existing files from the legacy `media/` directory into the bucket, **preserving keys**:
   ```sh
   aws s3 cp --recursive ./media/ s3://$BUCKET/ \
       --endpoint-url=$ENDPOINT \
       --region=$REGION
   ```
   (Or use `rclone`, `s5cmd`, or any S3-compatible client.) Random spot-check via `python manage.py shell -c "from django.core.files.storage import default_storage; print(default_storage.exists('menu_items/<key>.jpg'))"`.
3. Smoke test admin upload, storefront PDP image, OAuth, Paystack on a staging Railway environment first.

---

## 6. Local development

No extra configuration required. With no `DATABASE_URL` and no `BUCKET` env var, settings fall back to:

- SQLite at `db.sqlite3`
- `FileSystemStorage` under `media/`
- `/media/` served by Django dev server

To dev against the staging Railway Postgres or bucket, copy the Railway env vars locally (do **not** commit them).

---

## 7. Switching to a custom API domain

When `api.<brand>.ng` is ready:

1. Add the custom domain on the Railway service (Railway issues TLS).
2. Update Railway variables: `BASE_URL=https://api.zmall.ng`, ensure `ALLOWED_HOSTS` includes the new host.
3. Update **third-party dashboards**:
   - Google OAuth: add `https://api.zmall.ng/accounts/google/login/callback/` (and any other tenants) to authorized redirect URIs.
   - Paystack: update callback URL.
4. Roll deploy. The old `*.up.railway.app` host can stay in `ALLOWED_HOSTS` until the change is verified.

---

## 8. Rollback

- Railway deploys are versioned. Use the dashboard "Redeploy" against the previous successful revision.
- If a release-phase migration fails, the deploy aborts before traffic shifts. Fix forward (new commit) rather than partial rollback to avoid data drift.
- For media: object keys are stable, so re-deploys never destroy uploads. Keep the bucket bound to the same Railway environment to retain content across deploys.

---

## 9. Smoke checklist after first Railway deploy

- [ ] `https://<base-url>/healthz/` returns 200.
- [ ] `python manage.py migrate --plan` shows no pending migrations after release.
- [ ] Admin login works (Unfold static loaded via WhiteNoise).
- [ ] Upload a Zmall MenuItem image in admin; the API returns a working absolute URL; the URL renders in the storefront.
- [ ] Google OAuth round-trips through `BASE_URL`.
- [ ] Paystack init/callback round-trips on a test transaction.
- [ ] `DEBUG=False` is enforced; security headers (HSTS, content-type-nosniff) appear in the response.
