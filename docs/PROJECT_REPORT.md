# Hospital Management System — Project Report

**Project title:** MediCare HMS — a role-based hospital management system
**Submitted by:** _[Student name]_, _[Roll number]_
**Course:** _[Course / semester]_
**Guide:** _[Guide name]_
**Institution:** _[College name]_
**Academic year:** _[Year]_

> Five pages of report content, arranged as the chapters a college report
> usually needs. Replace the bracketed placeholders, then paste each page into
> your report template.

---

## Page 1 — Abstract, introduction and objectives

### Abstract

Hospitals still lose time to telephone bookings, paper appointment registers and
medical files that live in one department only. MediCare HMS is a web-based
hospital management system that brings appointment scheduling, doctor
availability, patient records and administration into one application. It is
built with Python Flask and SQLite on the server and Bootstrap 5 on the client,
and it separates the hospital into three role-based portals: an administrator
who runs the hospital's master data, doctors who publish availability and record
clinical notes, and patients who book consultations and read their own medical
history. The system enforces its rules on the server and in the database: only
published slots can be booked, a patient cannot book the same slot twice, a
completed visit keeps its treatment record and its time, and no patient can read
another patient's history. The project demonstrates a complete, locally
runnable hospital workflow with authentication, authorization, search, reporting
and a responsive interface.

### Introduction

A hospital management system (HMS) is the software layer that coordinates the
people, time and records of a hospital. Even a small outpatient department needs
to answer four questions reliably: *who is available*, *who is booked*, *what
happened during the visit*, and *who is allowed to know*. Paper registers answer
the first three slowly and the fourth not at all.

This project implements those four questions as a single Flask application.
Administrators register doctors and departments; doctors publish consultation
slots for the next seven days; patients register themselves, search for a
specialist and book one of those slots; after the consultation the doctor marks
the appointment completed and writes the diagnosis, prescription, plan and
notes; the patient can then read that record at any time. Every action is
recorded against the person who performed it and protected by role-based access
control.

### Objectives

1. Provide three secure, separate portals (administrator, doctor, patient) with
   one login form and role-based redirection.
2. Let the administrator manage doctors, departments, patients and appointments,
   including safe retirement and deactivation instead of destructive deletion.
3. Let doctors publish their availability and manage only their own bookings.
4. Let patients search doctors, book a published slot, reschedule or cancel it,
   and read their own medical history.
5. Prevent appointment conflicts at both application and database level.
6. Keep medical history immutable in practice: cancellation is a status change,
   completed visits cannot be deleted, and treatment records are tied to the
   appointment that produced them.
7. Deliver a professional, responsive Bootstrap interface that can be
   demonstrated on a laptop and a phone.

### Scope

The system covers outpatient appointment management and clinical record keeping.
It deliberately excludes inpatient admission, billing/invoicing, pharmacy stock,
laboratory interfaces and insurance claims; these are listed as future work.
The application runs locally against SQLite and needs no paid service.

---

## Page 2 — Literature review, technology stack and requirements

### Review of existing approaches

Commercial hospital information systems (for example, full HIS/EMR suites) offer
billing, pharmacy and laboratory modules, but they are expensive, require
database servers and are hard to demonstrate in an academic setting. Generic
appointment-booking products handle calendars well but do not model clinical
records or hospital staff. Open-source Flask examples often stop at CRUD screens
without enforcing scheduling rules. This project fills that gap: it is small
enough to run on a laptop with SQLite, yet it models the complete outpatient
flow — availability, booking, consultation, record — with the rules enforced in
one place.

### Technology stack

| Component | Technology | Reason |
|---|---|---|
| Backend | Python 3, Flask 3 | Lightweight, explicit routing, ideal for teaching the request/response cycle |
| Architecture | Application factory + blueprints | Separates the three portals and keeps configuration testable |
| ORM | Flask-SQLAlchemy (SQLAlchemy 2) | Relationships and constraints expressed in Python, portable SQL |
| Database | SQLite | Zero configuration, single file, included with Python |
| Authentication | Flask-Login, Werkzeug hashing | Session management without storing plain-text passwords |
| Forms | Flask-WTF / WTForms | Server-side validation and CSRF protection |
| Frontend | Jinja2, Bootstrap 5.3, Bootstrap Icons, custom CSS | Responsive components without a JavaScript build step |
| Charts | Chart.js (CDN) | One dashboard chart, no extra dependency |
| Configuration | python-dotenv | Secrets and admin credentials outside source control |

### Functional requirements

- **FR1** The administrator signs in with a seeded account; there is no admin
  registration.
- **FR2** Patients register with name, email, phone and password; a patient ID
  is generated automatically.
- **FR3** The administrator creates doctors with a linked login account and can
  edit, deactivate or (only without history) delete them.
- **FR4** The administrator creates and retires departments, but cannot retire a
  department that still has active doctors.
- **FR5** Doctors publish, edit, hide and delete slots for the next seven days.
- **FR6** Patients search doctors by name, specialization or department, and book
  one of the published slots.
- **FR7** The system prevents duplicate and conflicting bookings.
- **FR8** Patients can reschedule or cancel a booked appointment before it
  starts.
- **FR9** Doctors complete today's or past appointments and cancel bookings.
- **FR10** Doctors write a treatment record only for a completed appointment
  they are assigned to.
- **FR11** Patients view their own diagnoses, prescriptions, plans and notes.
- **FR12** The administrator can read all treatment records but cannot edit them.

### Non-functional requirements

- **Security:** hashed passwords, CSRF tokens, role checks, ownership checks,
  safe redirects, `no-store` on admin pages.
- **Integrity:** foreign keys, check constraints and partial unique indexes.
- **Usability:** flash messages, confirmation modals, empty states, responsive
  tables and a mobile sidebar.
- **Portability:** one `pip install -r requirements.txt`, no external services.
- **Maintainability:** business rules in `app/services`, thin route functions.

---

## Page 3 — System design

### Architecture

The application follows a layered MVC-style structure:

```
Browser (Bootstrap 5 + Chart.js)
        │  HTTP, CSRF token
        ▼
Flask blueprints (main, auth, admin, doctor, patient)
        │  validate form → call service → render template
        ▼
Service layer (availability, appointments, treatments, doctors,
               patients, departments, statistics)
        │  business rules, ownership, transactions
        ▼
SQLAlchemy models ──► SQLite (instance/hms.sqlite3)
```

Routes do four things only: check the role, load the record with an ownership
scope, call a service function, and choose a template or redirect. All rules
that must not be bypassed — booking capacity, duplicate prevention, completion
rules, treatment ownership — live in the service layer so the same function is
used by the web request and by the test script.

### Data model

Seven tables: `users`, `departments`, `doctors`, `patients`,
`doctor_availability`, `appointments`, `treatments`.

- `users` holds authentication and account state; `doctors` and `patients` are
  optional one-to-one profiles, so one login table serves three roles.
- A doctor belongs to a department; a department cannot be deleted while staffed
  (`ON DELETE RESTRICT`).
- A doctor publishes many availability slots; a slot belongs to exactly one
  doctor and is unique per date and start time.
- An appointment joins one patient, one doctor and (optionally) the slot it was
  booked from. It has three states: `booked`, `completed`, `cancelled`.
- A treatment belongs to exactly one appointment (`UNIQUE appointment_id`) and
  records the doctor who wrote it.

The full Mermaid ER diagram is in [ER_DIAGRAM.md](ER_DIAGRAM.md).

### Key design decisions

1. **Cancellation is a status change, not a delete.** History survives, and the
   partial unique index `uq_active_doctor_slot` only covers non-cancelled rows,
   so cancelling frees the time for someone else.
2. **Bookings reference slots, not free text.** The date and time come from the
   slot, so a patient cannot invent a time the doctor never published.
3. **Completion is one-way.** A completed appointment cannot be cancelled,
   rescheduled, completed again or deleted; treatment records are allowed only
   after completion.
4. **One clinical record per visit.** `UNIQUE appointment_id` plus an
   edit-in-place form; the record's author is stored separately for audit.
5. **Scoped lookups return 404.** `filter_by(id=..., doctor_id=current)`
   combines authorization and fetch, and avoids revealing that a foreign record
   exists.
6. **Deactivate instead of delete.** Doctors with history and all patients keep
   their rows; departments are retired. Only a doctor with no appointments and
   no treatments can be deleted.

### User interface design

The interface uses a dashboard shell: fixed sidebar on desktop, slide-in drawer
below 992 px, sticky topbar with the signed-in user, card-based content and
Bootstrap tables that scroll horizontally on small screens. Status is always
shown as a coloured badge with a text label, so colour is not the only signal.
Destructive actions go through a confirmation modal that submits a CSRF-protected
form.

---

## Page 4 — Implementation and testing

### Implementation highlights

**Authentication and roles.** One login form queries `users` by email, checks the
Werkzeug hash and redirects by role. `role_required(*roles)` wraps every
protected view: anonymous users are redirected to login with `next`, the wrong
role gets a 403 page, and an account deactivated while signed in is logged out
with an explanation. Because Flask-Login's `is_authenticated` mirrors
`is_active`, the decorator checks `is_anonymous` explicitly — otherwise a
deactivated user would see a generic login prompt instead of the real reason.

**Availability.** A doctor publishes slots inside a seven-day window between
08:00 and 21:00. The service rejects overlaps with the doctor's other slots,
times in the past, end times before start times, and capacities that leave less
than five minutes per patient. A slot with bookings cannot be moved, hidden or
deleted.

**Booking.** `book_slot()` re-validates the slot, rejects duplicates for the same
patient, checks capacity, derives the appointment time from the slot (offsetting
each patient inside a multi-patient slot) and commits. A `try/except
IntegrityError` converts a race with another request into a friendly "that time
was just taken" message. Two partial unique indexes make double booking
impossible even if the application check is bypassed.

**Appointments and records.** Doctors see upcoming/today/week/all views and can
complete only booked appointments dated today or earlier. Patients can
reschedule into another open slot of the same doctor; the service re-checks the
target slot and the database index is the final guard. Treatment records accept
only completed visits, only from the assigned doctor, and follow-up dates cannot
precede the visit.

**Search.** SQL `ILIKE` filters cover doctor name/specialization, patient
name/ID/phone, appointment text/doctor/patient/status/date range, and treatment
diagnosis/prescription/patient/doctor. Pagination is implemented with
`db.paginate`, and the pagination macro preserves active filters.

### Testing strategy

Testing combined automated checks with a live server run.

1. **Automated system test (140 checks, in-memory SQLite, CSRF disabled).**
   Covered seeding idempotency, all three logins, registration validation,
   duplicate email, wrong password, deactivated login, the full role matrix
   (403s), department create/rename/retire rules, doctor create/edit/
   deactivate/guarded delete, patient search/edit/deactivate, availability
   window/overlap/capacity/hide rules, booking, duplicate booking, capacity,
   database unique index, reschedule, cancellation, completion rules, treatment
   create/edit and ownership, patient privacy (404 for foreign records), admin
   filters and read-only treatment access, plus a crawl of every internal link
   for public, admin, doctor and patient sessions (no broken links).
2. **Live run (file-backed SQLite, real CSRF tokens).** Exercised registration,
   login, booking, reschedule, cancellation, appointment completion, treatment
   entry, patient record viewing and all administrator list/detail pages through
   HTTP.
3. **Manual checklist.** [TESTING_CHECKLIST.md](TESTING_CHECKLIST.md) lists the
   steps and expected results for a viva demonstration, including browser and
   mobile-width checks that automation cannot judge.

### Defects found and fixed during final testing

| Defect | Fix |
|---|---|
| `doctor.profile` and `patient.profile` sidebar items had no routes and stayed disabled ("soon") | Added read-only profile pages for both roles |
| Non-completed visits could be reached by typing the treatment URL (the link was hidden) | Route now redirects with an explanation, and the service raises `ValueError` |
| Follow-up date could be set before the visit date | Form `min` attribute plus a service check |
| Rescheduling accepted any slot id if the form choices were bypassed | Service re-validates same doctor, future, active, capacity and duplicate |
| Invalid date range on the admin appointment filter caused a confusing empty list | Inline validation error, invalid dates ignored |
| Mobile navigation placeholder ("soon") items looked broken | Real routes added; remaining navigation items all resolve |

---

## Page 5 — Results, limitations, future scope and conclusion

### Results

The delivered system runs locally with one command after `pip install -r
requirements.txt`. Starting the app creates the SQLite database and seeds the
administrator and eight departments; `python seed_demo.py` adds two doctors, two
patients, published slots, a completed visit with a treatment record, an
upcoming booking and a cancelled booking for demonstration.

All functional requirements FR1–FR12 were exercised and passed in the automated
system test (140/140 checks) and in a live HTTP session with CSRF enabled. The
link crawl walked 48 administrator pages, 25 doctor pages, 13 patient pages and
3 public pages without a single 4xx response, which confirms that navigation,
`url_for` targets and templates agree.

Performance is adequate for a college demonstration: list pages are paginated,
queries are scoped by doctor/patient and indexed on the foreign keys and dates,
and the dashboard uses a handful of aggregate queries. Because the workload is
tiny, no benchmarking was claimed.

### Limitations

- SQLite is single-file and not suited to concurrent production traffic.
- One doctor per appointment; there is no multi-doctor consultation or referral
  workflow.
- Prescriptions and notes are free text rather than structured medicine items,
  so there is no dosage interaction checking.
- No email/SMS notifications, billing, pharmacy, laboratory or inpatient module.
- UI was verified by rendering and responsive markup, not by a formal
  accessibility audit (no screen-reader or contrast testing was performed).

### Future scope

1. Migrate to PostgreSQL and add Flask-Migrate for versioned schema changes.
2. Structured prescriptions (medicine, dose, frequency, duration) with printable
   PDFs.
3. Email/SMS reminders and calendar invites.
4. Doctor-side patient messaging and follow-up scheduling.
5. Billing and invoice generation linked to completed appointments.
6. Two-factor authentication for administrator accounts.
7. Accessibility audit and keyboard-navigation improvements.

### Conclusion

MediCare HMS demonstrates that a compact Flask application can implement a
complete, rule-enforced hospital outpatient workflow. The value of the project
is not the number of screens but the discipline behind them: a single service
layer owns the scheduling and clinical rules, the database enforces the same
invariants, and every route is scoped to the person allowed to see the record.
The result is a system that is small enough to understand in a viva, yet honest
about its limits — it is a teaching-quality outpatient HMS, not a replacement
for a hospital's commercial information system.

### References

1. Flask documentation — <https://flask.palletsprojects.com/>
2. SQLAlchemy 2.0 documentation — <https://docs.sqlalchemy.org/>
3. Flask-SQLAlchemy — <https://flask-sqlalchemy.palletsprojects.com/>
4. Flask-Login — <https://flask-login.readthedocs.io/>
5. Flask-WTF and WTForms — <https://flask-wtf.readthedocs.io/>
6. Bootstrap 5 documentation — <https://getbootstrap.com/docs/5.3/>
7. OWASP Top 10 (2021) — <https://owasp.org/www-project-top-ten/>
8. SQLite foreign keys and partial indexes — <https://www.sqlite.org/>
