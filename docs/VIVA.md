# Viva questions and answers

Grouped by topic. Answers are written the way you would say them aloud — keep
them short, then point at the code or the screen if the examiner asks for proof.

## Architecture and Flask

**1. Why did you use Flask instead of Django?**
Flask is minimal and explicit: every route, model and form is visible in the
project, which makes it easier to explain in a viva. Django's admin and ORM
would generate much of the CRUD for us, but then the project would be mostly
configuration. Flask also matches the project constraint (Python + SQLite).

**2. What is the application factory pattern and why use it?**
`create_app()` in `app/__init__.py` builds the Flask app: it loads a config
class, initialises extensions, registers blueprints, CLI commands, error
handlers and the database bootstrap. It means we can create a fresh app for
tests with `create_app("testing")` using an in-memory database, without touching
the real file.

**3. What are blueprints and how are they used here?**
A blueprint is a group of routes with a URL prefix. We have five: `main`,
`auth`, `admin` (`/admin`), `doctor` (`/doctor`) and `patient` (`/patient`). It
keeps each role's code separate and makes the endpoint names (`admin.doctors`,
`patient.records`) readable in templates.

**4. Explain the request flow for booking an appointment.**
The patient clicks Book → POST `/patient/book/<slot_id>` → `role_required`
checks the session and role → `book_slot()` in `availability_service` validates
the slot, duplicates, capacity and derives the time → the appointment row is
inserted and committed → flash message → redirect to the confirmation page
(`POST → Redirect → GET` pattern, so refreshing does not book twice).

**5. What is Jinja2 and how do templates avoid repetition?**
Jinja2 is Flask's template engine. `base.html` holds the document shell,
`layouts/dashboard.html` adds the sidebar/topbar, `partials/` holds reusable
pieces (flash messages, form field macro, confirmation modal) and
`partials/_macros.html` defines macros such as `status_badge` and
`empty_state`.

## Database and models

**6. Why seven tables instead of one `users` table with all columns?**
Authentication columns are shared by all three roles; doctor and patient data
are different. Putting profiles in `doctors` and `patients`, each one-to-one
with `users`, avoids a wide table full of nullable columns and keeps role data
typed and constrained.

**7. How is the one-to-one relationship enforced?**
`doctors.user_id` and `patients.user_id` are `UNIQUE` foreign keys to
`users.id`, and the relationship uses `uselist=False`. A user can therefore have
at most one profile of each kind.

**8. What happens when a doctor is deleted?**
`doctor_service.delete_doctor` first checks for appointments and treatments; if
any exist it raises an error and the view shows a warning. If the doctor has no
history, the user row is deleted and the doctor profile is removed by
`cascade="all, delete-orphan"`. Departments use `ON DELETE RESTRICT` so a
staffed department cannot be deleted at all.

**9. Where are the database constraints defined?**
In the models: `CheckConstraint` for roles, appointment status, gender,
availability time order and non-negative fees; `UniqueConstraint` for
`(doctor_id, available_date, start_time)`; and two **partial unique indexes**
on `appointments` for active bookings.

**10. Explain the partial unique index.**
A normal `UNIQUE(doctor_id, date, time)` would also block booking the same time
after a cancellation. The index is created with
`sqlite_where=status != 'cancelled'`, so only active (booked/completed) rows are
indexed. Cancelling removes the row from the index and frees the time, while
the database still refuses a real double booking.

**11. How did you change the schema when a later task added a column?**
`ensure_schema_upgrades()` in `app/utils/bootstrap.py` inspects the database and
runs small additive SQLite `ALTER TABLE`/`CREATE INDEX IF NOT EXISTS` statements.
`db.create_all()` only creates missing tables, so this keeps an existing
database usable without a migration tool. A production project would use
Flask-Migrate.

**12. What is a transaction and where do you use one?**
A transaction groups SQL statements so they succeed or fail together.
`db.session.commit()` closes one; on `IntegrityError` we call
`db.session.rollback()` so the session is not left broken — for example when a
slot is taken by a simultaneous request.

## Security

**13. How are passwords stored?**
`User.set_password` uses `werkzeug.security.generate_password_hash`
(PBKDF2 by default) and only the hash is stored. `check_password` compares
hashes; the plain password is never written to the database or a template.

**14. How is role-based access enforced?**
`@role_required(Role.ADMIN)` wraps a view and checks: anonymous → redirect to
login; inactive/blacklisted → log out with a message; wrong role → 403; else
run the view. Templates also hide links, but that is cosmetic — the server
check is what matters.

**15. Why does the decorator check `is_anonymous` instead of using
`@login_required`?**
Flask-Login's `UserMixin.is_authenticated` returns `is_active`, so a deactivated
account would be treated as anonymous and get a generic login prompt. Checking
`is_anonymous` lets us detect a real session whose account was disabled and
clear it with an explanation.

**16. How do you stop a doctor reading another doctor's appointment?**
The lookup is scoped: `Appointment.query.filter_by(id=..., doctor_id=doctor.id)
.first_or_404()`. Fetch and authorisation are the same query, so there is no
"check then fetch" gap. A foreign id returns 404, not 403, so the existence of
another record is not revealed.

**17. How are patients prevented from reading someone else's medical history?**
`treatment_service.patient_treatment()` joins `Treatment` to `Appointment` and
filters `Appointment.patient_id == current patient`. A foreign treatment id
returns 404. The doctor's patient page is similarly limited to patients who have
an appointment with that doctor.

**18. What is CSRF and how is it prevented?**
Cross-Site Request Forgery tricks a signed-in browser into sending a state-
changing request. Flask-WTF's `CSRFProtect` issues a token per session; every
POST form includes `csrf_token`, and a request without a valid token gets 400.
That is why all destructive actions are POSTs, not links.

**19. Why are administrator pages sent with `Cache-Control: no-store`?**
They contain patient data. `no-store` stops the browser from keeping a copy that
could be seen after logout on a shared computer. It is implemented as an
`after_request` hook on the admin blueprint.

**20. What is the safe-redirect check for?**
After login we honour `?next=`, but only if it points to the same host.
`is_safe_redirect` rejects absolute URLs to other sites, preventing an open
redirect that could be used for phishing.

## Appointments and scheduling

**21. How do you prevent booking the same appointment twice?**
Three layers: the patient's own list hides the slot they already hold, the
booking service rejects an active appointment for the same patient and slot, and
the partial unique index `uq_active_patient_slot` enforces it in the database.

**22. Why does booking take a slot id instead of a date and time?**
The date and time come from the slot the doctor published. If the browser sent
them, a patient could craft a request for an arbitrary time. Deriving them from
the slot makes "no booking outside published availability" a property of the
design rather than a validation rule.

**23. How does a multi-patient slot assign times?**
The slot duration is divided by capacity and each booking is offset by that
step (with a minimum of one minute), so two patients in a 30-minute slot get
09:00 and 09:15. This also keeps the per-moment unique index satisfied.

**24. What happens to a cancelled appointment?**
`status` changes to `cancelled` and `cancel_reason` is stored. The row remains
as history, it stops counting towards `booked_count`, it leaves the partial
unique index, and the slot becomes bookable again. Nothing is deleted.

**25. Can a completed appointment be cancelled or deleted?**
No. The service accepts only `booked` appointments for cancellation and
rescheduling, a model event blocks deleting a completed appointment, and the
database still counts completed rows as occupying their time.

**26. How does rescheduling avoid conflicts?**
`reschedule_appointment` re-validates that the new slot is the same doctor's,
future, active and not full, checks the patient doesn't already hold it, and
commits; an `IntegrityError` is converted into "that time was just taken". The
appointment row is updated in place, so the record's history stays attached.

**27. Why can a treatment only be written after completion?**
A diagnosis before the consultation would be fiction and would allow completing
a visit without seeing the patient. The route redirects if the status is not
`completed`, and `save_treatment` raises `ValueError` if it is called directly.

## Forms, templates and UI

**28. How is form validation done?**
WTForms validators (`DataRequired`, `Length`, `Email`, `Regexp`,
`NumberRange`, `EqualTo`, custom `validate_<field>` methods) run on the server
in `form.validate_on_submit()`. HTML5 attributes are only a convenience.
Business rules that need other records (duplicate email against the database,
overlapping slots, date range order) live in custom validators or the service.

**29. How is the layout responsive?**
Bootstrap's grid (`col-6 col-xl-3`), `table-responsive` wrappers,
`.d-none .d-sm-block` helpers and a custom media-query block. Below 992 px the
sidebar becomes a slide-in drawer toggled by a hamburger button, with a backdrop,
Escape-to-close and ARIA attributes.

**30. How does the confirmation modal work without extra JavaScript?**
Buttons carry `data-confirm-form="#someForm"`, `data-confirm-title`,
`data-confirm-text`, tone and label. `main.js` opens one Bootstrap modal, fills
it with those values, and submits the referenced form (which already contains
the CSRF token) when the user confirms.

**31. What is the `available_endpoints` template global?**
A set of registered endpoint names injected by a context processor. Sidebar
macros check it before calling `url_for`, so a link whose route has not been
built yet renders as a disabled "soon" item instead of raising `BuildError`.
At the end of the project every sidebar link resolves.

## Testing and project management

**32. How did you test the system?**
An automated script (140 checks) ran the whole workflow against an in-memory
SQLite database: logins, role matrix, CRUD, validation, booking conflicts,
rescheduling, completion, treatment ownership, patient privacy, admin filters
and a crawl of every internal link for all roles. A separate live run used a
real database and CSRF tokens. The manual checklist covers browser and mobile
checks.

**33. What was the hardest bug you fixed?**
The cancellation/double-booking conflict: a plain unique constraint blocked
re-booking a cancelled time. The fix was a partial unique index that only covers
non-cancelled rows, combined with `booked_count` ignoring cancelled
appointments, so the "slot is free" state is consistent in both the database and
the UI.

**34. Why keep business rules in `services/` instead of the routes?**
Routes then stay short and the same rule is used by the web request and the
tests. It also prevents a rule from being enforced on one screen and forgotten
on another (for example, booking versus rescheduling).

**35. What would you do differently with more time?**
Move to PostgreSQL with Flask-Migrate, add structured prescriptions with PDF
output, notifications, billing, and run an accessibility audit. I would also add
pytest-based unit tests checked into the repository instead of a throwaway
system script.
