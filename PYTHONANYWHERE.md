# Deploying Chopsticks Backend on PythonAnywhere

Steps to run this Django project on PythonAnywhere and serve all tenants (Chopsticks & Bowls, Roschi Water, Zmall).

---

## 1. Create the app and clone (or upload) code

- In the **Web** tab, add a new web app, choose **Manual configuration** and **Python 3.10** (or the version you use).
- In **Consoles** or **Files**, clone your repo or upload the project so the backend lives at e.g.:
  - `/home/YOUR_USERNAME/chopsticks_backend/`
- Ensure the project has a virtualenv and `requirements.txt` at the repo root.

---

## 2. Virtualenv and dependencies

In a **Bash** console:

```bash
cd /home/YOUR_USERNAME/chopsticks_backend
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

In the **Web** tab → **Virtualenv**, set the path to:
`/home/YOUR_USERNAME/chopsticks_backend/venv`

---

## 3. Environment variables (.env)

- Copy the production template and edit it on the server (do not commit real `.env`):

```bash
cp .env.prod.template .env
```

- Edit `.env` and replace:
  - `YOUR_PA_USERNAME` → your PythonAnywhere username (in `ALLOWED_HOSTS`, `BASE_URL`, `OAUTH_BASE_URL`).
  - `SECRET_KEY` → generate a new one:  
    `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
  - `DEBUG=False` (must stay False in production).
  - SMTP, Google OAuth, Paystack live keys, etc., as needed.

- Ensure **WSGI file** is loaded from the project so Django can read `.env` from the project directory (python-decouple looks for it in the current working directory; PA usually sets `project_home` and adds it to `sys.path`; the app’s working directory is typically the project root when the WSGI app runs).

---

## 4. WSGI configuration

In the **Web** tab, open the **WSGI configuration file** (e.g. `/var/www/YOUR_USERNAME_pythonanywhere_com_wsgi.py`). Point it at your Django project and app. Example:

```python
import os
import sys

path = '/home/YOUR_USERNAME/chopsticks_backend'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chopsticks_backend.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

Replace `YOUR_USERNAME` with your PA username. Ensure the project directory is on `sys.path` and `DJANGO_SETTINGS_MODULE` matches your settings module.

---

## 5. Static and media files (required)

Django does not serve static/media when `DEBUG=False`. Use PythonAnywhere’s **Static files** mappings so the PA server serves them.

In the **Web** tab → **Static files**:

| URL        | Directory (absolute path) |
|-----------|----------------------------|
| `/static/` | `/home/YOUR_USERNAME/chopsticks_backend/staticfiles` |
| `/media/`  | `/home/YOUR_USERNAME/chopsticks_backend/media`      |

Replace `YOUR_USERNAME` in the paths. Then click **Reload** for your web app so the new mappings apply.

---

## 6. Collect static files

Run once (and again after any change to admin/Unfold or other static assets):

```bash
cd /home/YOUR_USERNAME/chopsticks_backend
source venv/bin/activate
python manage.py collectstatic --noinput
```

This fills `staticfiles/` so `/static/` (admin, Unfold, etc.) works.

---

## 7. Database and migrations

- If using SQLite: ensure `db.sqlite3` is in the project directory (or set `DATABASE_NAME` in settings to the correct path). Do **not** commit `db.sqlite3`; create it on the server or copy it securely if restoring.
- Run migrations:

```bash
python manage.py migrate
```

- Create a superuser if needed:

```bash
python manage.py createsuperuser
```

---

## 8. Tenant configuration (multi-tenant)

- Open Django admin (e.g. `https://YOUR_USERNAME.pythonanywhere.com/admin/` or your main admin URL).
- For each business (Chopsticks & Bowls, Roschi Water, Zmall):
  - Create or edit a **RestaurantSettings** record.
  - Set **domain** to the site’s primary domain (e.g. `zmall.ng`, `www.zmall.ng`, `chopsticksandbowls.com`).
  - Add business-specific **Paystack** keys and any other per-tenant settings.
- Frontends must call the API using this backend’s base URL; the backend identifies the tenant from the request (e.g. domain or header) and uses the matching RestaurantSettings.

---

## 9. Reload the web app

After any change to code, `.env`, or Static files mappings:

- **Web** tab → **Reload** your web app.

---

## Checklist

- [ ] Code in `/home/YOUR_USERNAME/chopsticks_backend/`
- [ ] Virtualenv set and `pip install -r requirements.txt` done
- [ ] `.env` created from `.env.prod.template`, `YOUR_PA_USERNAME` and secrets replaced, `DEBUG=False`
- [ ] WSGI file points at `chopsticks_backend` and `DJANGO_SETTINGS_MODULE`
- [ ] Static files: `/static/` → `.../staticfiles`, `/media/` → `.../media`
- [ ] `python manage.py collectstatic --noinput`
- [ ] `python manage.py migrate`
- [ ] Superuser and RestaurantSettings (domains + Paystack) configured for each tenant
- [ ] Web app reloaded

---

## Troubleshooting

- **502 / import errors:** Check the **Error log** in the Web tab; fix virtualenv path, `DJANGO_SETTINGS_MODULE`, or missing packages.
- **404 for `/static/` or `/media/`:** Confirm Static files mappings and that you ran `collectstatic` (for `/static/`). Ensure paths use your real PA username and that the app was reloaded.
- **Admin assets missing:** Run `collectstatic` again and reload; ensure WhiteNoise is in `requirements.txt` and middleware is enabled (static is still served by PA from `staticfiles/` when the mapping is set).
