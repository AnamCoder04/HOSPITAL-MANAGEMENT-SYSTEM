# MediCare HMS — Hospital Management System

A complete hospital management system built with **Python Flask**, **SQLite** and
**Bootstrap 5**, with three separate portals for administrators, doctors and
patients. Patients register themselves, search doctors, book published slots and
read their own medical records; doctors publish availability, manage their
appointments and write treatment records; the administrator runs doctors,
departments, patients, appointments and reads every clinical record.

Everything runs locally against a single SQLite file — no database server, no
external services, no JavaScript build step.

---

## 1. Features

### Administrator
- Seeded admin account (no admin registration).
- Dashboard with live counts and an appointment status chart (Chart.js).
- **Doctors**: create with a linked login (generated or manual password), edit,
  activate/deactivate, guarded delete (only without history), search and
  specialization filter.
- **Departments**: create, rename, describe, retire/reactivate (retiring is
  refused while active doctors still work there).
- **Patients**: paginated search by name / patient ID / phone, profile with
  appointment and treatment history, edit details, deactivate/reactivate
  (patients are never deleted).
- **Appointments**: search text, doctor / patient / status / date-range filters,
  pagination, details, cancellation with a reason.
- **Treatment records**: every clinical record, searchable, filterable by doctor
  and patient, read-only.

### Doctor
- Dashboard with today's schedule.
- **Appointments**: upcoming / today / this week / all, status and patient-name
  filters, mark completed (today or earlier, booked only), cancel with reason.
- **Availability**: publish, edit, hide/show and delete slots for the next seven
  days; booked slots keep their date and time.
- **My patients**: everyone seen through an appointment, with visit counts.
- **Medical history**: complete cross-doctor history for a patient, plus a form
  to write/update the diagnosis, prescription, treatment plan, notes and
  follow-up date for a completed visit.
- **My profile**: read-only professional profile.

### Patient
- Self-registration with an automatically generated patient ID (`PAT-000001`).
- Search doctors by name, specialization or department, open a profile and see
  the next seven days of open slots.
- Book a slot, confirmation page, reschedule to another open slot, cancel.
- **Medical records**: own history timeline, completed visits, and a readable
  record page with diagnosis, prescription, plan, notes and follow-up.
- **My profile**: read-only account and medical profile.

### Cross-cutting
- Role-based access control on every protected route, with ownership checks
  inside views (another user's id returns 404, not 403).
- Server-side form validation (WTForms) plus database constraints and partial
  unique indexes against double booking.
- Flash messages, confirmation modals, empty states, responsive Bootstrap
  tables/cards, mobile sidebar drawer.
- Passwords hashed with Werkzeug; CSRF protection on every POST; admin pages
  send `Cache-Control: no-store`.

---

## 2. Technology stack

| Layer | Choice |
|---|---|
| Language | Python 3.10+ (developed on 3.12) |
| Web framework | Flask 3 (application factory, blueprints) |
| ORM | Flask-SQLAlchemy 3 / SQLAlchemy 2 |
| Database | SQLite (`instance/hms.sqlite3`) |
| Auth | Flask-Login + Werkzeug password hashing |
| Forms | Flask-WTF / WTForms |
| Frontend | Jinja2, Bootstrap 5.3, Bootstrap Icons, Inter, custom CSS |
| Charts | Chart.js (admin dashboard only, CDN) |
| Config | python-dotenv |

No React/Vue/Node, no MySQL/PostgreSQL, no external API is required.

---

## 3. Project structure

```
HOSPITAL-MANAGEMENT-SYSTEM/
├── app/
│   ├── __init__.py              # application factory, blueprints, error pages
│   ├── cli.py                   # `flask init-db`
│   ├── extensions.py            # db, login_manager, csrf
│   ├── blueprints/
│   │   ├── main/routes.py       # public landing page
│   │   ├── auth/                # login, patient registration, logout
│   │   ├── admin/               # dashboard, doctors, patients, departments,
│   │   │                        # appointments, treatment records
│   │   ├── doctor/              # dashboard, appointments, availability,
│   │   │                        # patients + history, treatment form, profile
│   │   └── patient/             # dashboard, doctor search, booking,
│   │                            # appointments, records, profile
│   ├── models/                  # User, Doctor, Patient, Department,
│   │                            # Appointment, DoctorAvailability, Treatment
│   ├── services/                # business rules (appointments, availability,
│   │                            # doctors, patients, departments, treatments,
│   │                            # dashboard statistics)
│   ├── templates/               # Jinja2: layouts, partials, per-role pages
│   ├── static/css/style.css     # design system + responsive rules
│   ├── static/js/main.js        # sidebar, flash, confirm modal
│   └── utils/                   # bootstrap, decorators, security helpers
├── docs/
│   ├── ARCHITECTURE.md          # design notes written during development
│   ├── PROJECT_REPORT.md        # five-page college report content
│   ├── ER_DIAGRAM.md            # Mermaid entity-relationship diagram
│   ├── API.md                   # endpoint documentation
│   ├── TESTING_CHECKLIST.md     # manual test plan
│   ├── VIVA.md                  # viva questions and answers
│   ├── VIDEO_SCRIPT.md          # ~5 minute demo narration
│   └── AI_DECLARATION.md        # AI/LLM usage declaration draft
├── config.py                    # environment configuration classes
├── run.py                       # entry point (`python run.py`)
├── seed_demo.py                 # idempotent demo data script
├── requirements.txt
├── .env.example
└── README.md
```

---

## 4. Setup

### 4.1 Prerequisites
- Python 3.10 or newer
- `pip` and `venv` (bundled with Python)
- A modern browser

### 4.2 Install

```bash
git clone https://github.com/AnamCoder04/HOSPITAL-MANAGEMENT-SYSTEM.git
cd HOSPITAL-MANAGEMENT-SYSTEM

python -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 4.3 Configure (optional)

The application runs with sensible defaults and no `.env` file. To override the
defaults, copy `.env.example` to `.env` and edit it:

```
SECRET_KEY=change-me-to-a-long-random-string
ADMIN_NAME=System Administrator
ADMIN_EMAIL=admin@medicare-hms.com
ADMIN_PASSWORD=Admin@12345
DATABASE_URL=sqlite:///hms.sqlite3
FLASK_CONFIG=development
```

### 4.4 Initialize the database

No migration tool is needed. Starting the application creates the SQLite file,
all tables, the seeded administrator and the starter departments:

```bash
flask --app run.py init-db
```

This is idempotent — running it again never duplicates rows and never resets a
password. (Simply running the app does the same initialization automatically.)

### 4.5 Demo data (recommended for evaluation)

```bash
python seed_demo.py
```

Creates two doctors, two patients, published slots for tomorrow, a completed
visit with a treatment record, an upcoming booking and a cancelled booking.
It is idempotent, so it can be run repeatedly.

### 4.6 Run

```bash
python run.py
# or
flask --app run.py run --debug
```

Open <http://127.0.0.1:5000>.

### 4.7 Default logins

| Role | Email | Password | Notes |
|---|---|---|---|
| Administrator | `admin@medicare-hms.com` | `Admin@12345` | Seeded on first start (`ADMIN_EMAIL` / `ADMIN_PASSWORD`) |
| Doctor | `ananya.sharma@medicare-demo.com` | `Doctor@123` | Created by `seed_demo.py` |
| Doctor | `vikram.rao@medicare-demo.com` | `Doctor@123` | Created by `seed_demo.py` |
| Patient | `rohit.verma@example.com` | `Patient@123` | Created by `seed_demo.py` |
| Patient | `meera.iyer@example.com` | `Patient@123` | Created by `seed_demo.py` |

Change the administrator password (via `.env`) before any real deployment.

---

## 5. Documentation

| Document | Contents |
|---|---|
| [docs/PROJECT_REPORT.md](docs/PROJECT_REPORT.md) | Five pages of report content (abstract, design, implementation, testing, conclusion) |
| [docs/ER_DIAGRAM.md](docs/ER_DIAGRAM.md) | Mermaid ER diagram and relationship rules |
| [docs/API.md](docs/API.md) | Every route, method, access level and parameters |
| [docs/TESTING_CHECKLIST.md](docs/TESTING_CHECKLIST.md) | Manual test plan with expected results |
| [docs/VIVA.md](docs/VIVA.md) | Viva questions with model answers |
| [docs/VIDEO_SCRIPT.md](docs/VIDEO_SCRIPT.md) | Five-minute presentation script |
| [docs/AI_DECLARATION.md](docs/AI_DECLARATION.md) | AI/LLM usage declaration draft |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Detailed design decisions per module |

---

## 6. Testing performed

The final build was checked with an automated, throwaway test script and a live
server run (both were removed before submission):

- **140 automated checks passed**: bootstrap/seeding idempotency, admin, doctor
  and patient login, registration validation, role matrix (403s), department
  create/rename/retire rules, doctor create/edit/deactivate/guarded delete,
  patient search/edit/deactivate, availability window/overlap/edit/hide rules,
  booking, duplicate booking, capacity, database unique index, reschedule,
  cancellation, completion rules, treatment create/edit and ownership, patient
  record privacy, admin filters, treatment read-only access, and a crawl of
  every internal link for all four session types — 3 public, 48 admin, 25
  doctor and 13 patient pages — with no broken links.
- **Live run with a real SQLite file and CSRF enabled** covered registration,
  login, booking, reschedule, cancellation, appointment completion, treatment
  entry, patient record viewing and admin views.
- UI was **not** inspected in a real browser during automated testing; the
  manual checklist includes the visual checks to perform before the viva. Layout
  uses Bootstrap's responsive grid, `table-responsive` wrappers and a
  slide-in sidebar below 992 px (see `app/static/css/style.css`).

Use [docs/TESTING_CHECKLIST.md](docs/TESTING_CHECKLIST.md) to reproduce the
manual checks.

---

## 7. Packaging for submission

From the project root (macOS/Linux):

```bash
zip -r hospital-management-system.zip . \
  -x ".venv/*" ".git/*" "instance/*" "__pycache__/*" "*/__pycache__/*" "*.pyc" ".env"
```

Windows PowerShell:

```powershell
Compress-Archive -Path * -DestinationPath hospital-management-system.zip `
  -Force
```

Before zipping: delete `.env` (it may contain a secret), keep `instance/` out
(the database is regenerated on first run), and confirm the archive opens with
`README.md`, `requirements.txt`, `run.py` at the top level. Full steps are in
[docs/TESTING_CHECKLIST.md](docs/TESTING_CHECKLIST.md#10-packaging-checklist).

---

## 8. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `ModuleNotFoundError: flask` | Virtual environment not activated, or `pip install -r requirements.txt` not run |
| Port 5000 already in use | `flask --app run.py run --port 5001` |
| Login fails with default credentials | `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `.env` differ from the values used to seed the existing database; use those or delete `instance/hms.sqlite3` and restart |
| `sqlite3.IntegrityError` after manual DB edits | Restore a clean database: stop the server, delete `instance/hms.sqlite3`, run `flask --app run.py init-db` and `python seed_demo.py` |
| "The CSRF token has expired" | Reload the page; tokens are tied to the session |
| Doctor missing from patient search | Doctor must be available and their department active |

---

## 9. License

Released under the MIT License — see [LICENSE](LICENSE).
