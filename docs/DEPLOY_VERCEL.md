# Deploying on Vercel

The project is configured to run as a **single Vercel Function** using the
Python runtime. Read the limitation in section 6 first — it decides whether
Vercel is the right host for your submission.

## 1. What was added

| File | Purpose |
|---|---|
| `index.py` | Entrypoint. Vercel looks for a top-level `app` in `index.py`; this file exports the same Flask app as `run.py`. |
| `vercel.json` | Sets the function's `maxDuration` to 60 s and memory to 1024 MB. |
| `.vercelignore` | Keeps `.venv/`, `.git/`, `instance/`, caches and `.env` out of the upload. |
| `.python-version` | Pins Python 3.12 (Vercel's default, tested locally with 3.12). |
| `config.py` | On Vercel (`VERCEL=1`) uses `sqlite:////tmp/medicare/hms.sqlite3`, marks cookies `Secure`, and enables demo seeding. |
| `app/__init__.py` | Creates the SQLite directory (`/tmp/medicare`), tolerates a read-only `instance/`, and seeds demo data when `AUTO_SEED_DEMO=1`. |

Local behaviour is unchanged: `python run.py` still uses
`instance/hms.sqlite3` and seeds nothing.

## 2. Deploy from the Vercel dashboard

1. Push the repository to GitHub.
2. In Vercel: **Add New → Project → Import** the repository.
3. Framework preset: **Flask** (detected from `index.py` + `requirements.txt`).
   Leave build/output settings empty; root directory is the repository root.
4. Add the environment variables from section 4 before the first deploy.
5. **Deploy**. The first request may take a few seconds while the function
   boots and creates the database.

## 3. Deploy with the CLI

```bash
npm install -g vercel        # CLI 48.2.10 or newer
vercel login
vercel link                  # choose the project (or create one)

# required secret (generate a value first)
vercel env add SECRET_KEY production
vercel env add ADMIN_EMAIL production
vercel env add ADMIN_PASSWORD production

vercel dev                   # local function emulation on http://localhost:3000
vercel --prod                # deploy to production
```

`vercel dev` runs the same `index.py` entrypoint as production, which is the
closest local approximation of the deployed function.

## 4. Environment variables

| Name | Required | Default | Notes |
|---|---|---|---|
| `SECRET_KEY` | Yes (strongly recommended) | insecure dev key | Session + CSRF signing. Generate with `python -c "import secrets; print(secrets.token_hex(32))"`. Changing it logs everyone out. |
| `ADMIN_EMAIL` | Recommended | `admin@medicare-hms.com` | Used only when the admin account is first created. |
| `ADMIN_PASSWORD` | Recommended | `Admin@12345` | Change it; the demo password is public in the README. |
| `ADMIN_NAME` | No | `System Administrator` | Display name. |
| `AUTO_SEED_DEMO` | No | `1` on Vercel | Seeds the demo doctors/patients/slots on a fresh instance. Set `0` for an empty hospital. |
| `FLASK_CONFIG` | No | `development` | Set `production` for `DEBUG=False` and secure cookies. |
| `DATABASE_URL` | No | `/tmp/medicare/hms.sqlite3` | Must stay on a writable path on Vercel; see section 6. |

Do not commit `.env`; Vercel injects these at runtime.

## 5. Post-deploy checks

1. `GET /` returns the landing page.
2. `/static/css/style.css` loads (Bootstrap/Inter come from CDNs).
3. Log in as the admin, open **Doctors**, **Patients**, **Appointments**.
4. Register a patient, book a slot, log in as a demo doctor, complete the
   appointment and write a record.
5. Open the record as the patient and as the admin.

If any of these fail, check **Deployments → Functions → Logs**; the app logs
`Database ready: admin=...` on every cold start.

## 6. The limitation you must know

**Vercel Functions have no persistent filesystem.** Only `/tmp` is writable, and
it is:

- wiped when the function instance is recycled (deploys, scaling down, idle
  timeouts), and
- **not shared** between concurrent instances.

Consequences for this project:

| Behaviour | On Vercel |
|---|---|
| Data written by one request | Visible only to the same warm instance; may disappear later |
| Demo data | Re-seeded automatically on a fresh instance (`AUTO_SEED_DEMO=1`) |
| Logins | A later request routed to another instance may not find the account and will appear signed out |
| SQLite writes | Concurrent instances writing the same logical data can conflict (each has its own file, so no corruption, but results diverge) |
| Uploads/background jobs | Not applicable — the project has none |

So Vercel is fine for **showing the UI and walking through a flow in one
sitting**, but it is not a reliable place for data you expect to keep. For a
graded viva where the examiner may refresh later, run the app locally or use a
host with a persistent disk.

### Options for a persistent deployment

1. **A host with a disk** (Render, Railway, Fly.io, a college VM): keep SQLite
   and point `DATABASE_URL` at the mounted disk, e.g.
   `sqlite:////var/data/hms.sqlite3`. No code changes needed.
2. **Managed Postgres**: set `DATABASE_URL` to the Postgres URL, but first move
   the two partial unique indexes from `sqlite_where` to `postgresql_where` in
   `app/models/appointment.py` (and guard `ensure_schema_upgrades`, which is
   SQLite-specific). This has **not** been implemented or tested in this
   project.
3. **Hosted SQLite-compatible database** (for example Turso/libSQL): requires
   adding a libSQL SQLAlchemy dialect and credentials. Also not implemented
   here.

Only option 1 works with the current code as-is.

## 7. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Build fails: `No python entrypoint found` | `index.py` is missing or was renamed; it must stay at the repository root and define `app`. |
| Function 500: `unable to open database file` | `DATABASE_URL` points somewhere read-only; use the default `/tmp/...` path on Vercel. |
| 400 on every login/register POST | CSRF cookie not sent; check that you are on `https://` and that `SESSION_COOKIE_SECURE` matches the scheme (it is `True` on Vercel). |
| Logged out after a few minutes | A different instance handled the request (see section 6). |
| Data disappeared after a new deployment | Expected: `/tmp` is per deployment instance. |
| Static CSS 404 | Confirm `/static/css/style.css` is reachable; Vercel routes it through the Flask function. |
| Cold start slow | Normal for serverless; the first request also creates the database and demo data. |

## 8. What was verified here — and what was not

Verified locally by simulating the Vercel environment (`VERCEL=1`):

- `index.py` imports and exposes the WSGI app; a plain WSGI server served `/`,
  `/auth/login` and `/static/css/style.css` with HTTP 200.
- The database is created at `/tmp/medicare/hms.sqlite3`, demo data is seeded,
  the admin can log in, a patient can register, and role pages return 200.
- With `VERCEL` unset, the app still uses `instance/hms.sqlite3`, does not
  auto-seed and does not set secure cookies.

**Not verified:** an actual deployment to Vercel (no Vercel account/token was
available in this environment), and therefore Vercel's build, function
packaging, cold-start timing and the multi-instance behaviour described above.
Follow section 5 after your first deploy.

## 9. Removing the deployment

```bash
vercel remove <project-name>
```

Or delete the project in the dashboard. Nothing here writes to an external
database, so removal deletes only the deployment.
