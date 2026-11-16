# Video presentation script (~5 minutes)

Record at 1280×720 in a single take if possible, with the app already running
and demo data seeded. Keep the mouse still while talking. Total ≈ 5:00.

---

## 0:00 – 0:20 · Opening

**On screen:** landing page `http://127.0.0.1:5000`

> "Hello, I'm _[name]_, and this is MediCare HMS, my hospital management system.
> It is built with Python Flask and SQLite, with a Bootstrap 5 interface, and it
> has three separate portals: administrator, doctor and patient. It runs locally
> with no external database or paid service."

## 0:20 – 0:45 · Problem and features

**On screen:** scroll the landing page features, then point at the login form.

> "Hospitals need to answer four questions reliably: who is available, who is
> booked, what happened during the visit, and who is allowed to know. This
> project implements all four: doctors publish availability, patients book a
> slot, doctors write the clinical record after the visit, and every route is
> protected by role and ownership checks."

## 0:45 – 1:25 · Administrator

**On screen:** log in as `admin@medicare-hms.com` / `Admin@12345`.

> "The administrator is seeded on first start — there is deliberately no admin
> registration. The dashboard shows live counts and the appointment status
> breakdown."

**On screen:** Doctors → open Dr. Ananya Sharma → show stats. Then Departments.

> "Under Doctors I can create a doctor with a linked login, edit their details,
> deactivate an account, or delete a doctor — but only if they have no medical
> history. Departments can be retired but not while active doctors still work
> there."

**On screen:** Patients → search "Rohit" → open profile.

> "Patients are searchable by name, patient ID or phone, and their profile shows
> appointment and treatment history. Patients are never deleted, only
> deactivated, because their records are medical history."

## 1:25 – 2:00 · Patient registration and search

**On screen:** open a private window, Register a new patient.

> "Patients register themselves. The patient ID is generated automatically, and
> the password is stored as a hash."

**On screen:** Find a doctor → filter by Cardiology → open the doctor → show
tomorrow's slots.

> "The doctor list only includes available doctors in active departments. Each
> profile shows the next seven days of published slots — nothing else can be
> booked."

## 2:00 – 2:35 · Booking rules

**On screen:** Book an open slot → confirmation page.

> "Booking takes a slot id, so the date and time always come from the slot the
> doctor published. The confirmation shows the doctor, department, room, fee and
> patient ID."

**On screen:** Go back and try the same slot again, then try a slot another
patient already holds.

> "Booking the same slot again is refused, and a full slot is refused for a
> second patient. The database also has a partial unique index, so even a
> crafted request cannot create a double booking."

## 2:35 – 3:10 · Doctor workflow

**On screen:** log in as the doctor → Appointments → Today → open appointment →
Mark completed.

> "Doctors see upcoming, today, this week or all appointments, but only their
> own. A future appointment cannot be completed — the button and the server both
> refuse it."

**On screen:** Write record → fill diagnosis, prescription, plan, notes,
follow-up → Save. Then open My patients → the patient.

> "Treatment details are accepted only for completed visits and only from the
> assigned doctor. The patient's history page shows records from every doctor,
> which is what a treating doctor needs, but only for patients they have
> actually seen."

## 3:10 – 3:40 · Patient records and privacy

**On screen:** log in as the patient → Medical records → open the record.

> "The patient sees their own diagnosis, prescription, treatment plan, notes and
> follow-up date. If I change the record id in the URL to another patient's, the
> server returns 404 — it does not even confirm that the record exists."

**On screen:** Try `/admin/dashboard` while signed in as the patient.

> "Role checks are on the server. A patient opening an admin page gets a 403
> page, not data."

## 3:40 – 4:15 · Reschedule, cancel and admin records

**On screen:** Patient → My appointments → Reschedule → confirm; show the old
slot becoming available on the doctor profile.

> "Rescheduling moves the same appointment to another open slot of the same
> doctor and releases the old time. Cancelling is a status change, never a
> delete, so the visit stays in the history while the slot is freed."

**On screen:** Admin → Treatment records → search/filter → open a record.

> "The administrator can read every clinical record for hospital oversight, but
> there is no edit route — clinical notes belong to the treating doctor."

## 4:15 – 4:40 · Database and rules

**On screen:** Switch to the ER diagram in `docs/ER_DIAGRAM.md` (or a slide).

> "There are seven tables. Users hold authentication; doctors and patients are
> optional one-to-one profiles. Appointments link one patient, one doctor and
> optionally the slot they were booked from. Treatments are one-to-one with an
> appointment and record their author. Integrity is enforced by foreign keys,
> check constraints and two partial unique indexes that ignore cancelled rows."

## 4:40 – 5:00 · Testing and close

**On screen:** `docs/TESTING_CHECKLIST.md` (or the terminal with the test
summary).

> "I verified the system with an automated end-to-end script covering 140 checks
> — logins, roles, CRUD, validation, booking conflicts, rescheduling, completion,
> treatment permissions and a crawl of every internal link — plus a live run with
> CSRF enabled. The manual checklist in the documentation covers the browser and
> mobile checks. The project installs with one requirements file and runs on
> SQLite. Thank you."

---

## Recording tips

- Prepare: `python seed_demo.py`, then start the server before recording.
- Have three browser windows ready: admin, doctor, patient (one private).
- Do not show the terminal output of a command you have not run.
- If a step fails on camera, say so and show the error — it is better than
  implying everything always works.
- Keep the video under 5:30; examiners often stop at five minutes.
