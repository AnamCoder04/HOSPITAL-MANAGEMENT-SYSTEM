# Manual testing checklist

Run through this list before the viva. Each row is a step and the result you
should see. Tick the box only after you have actually seen the result.

**Setup**

```bash
source .venv/bin/activate
flask --app run.py init-db
python seed_demo.py
python run.py
```

Open <http://127.0.0.1:5000>. Keep a second browser profile (or private window)
for the patient and doctor sessions.

## 1. Authentication and authorization

| # | Step | Expected | Done |
|---|---|---|---|
| 1.1 | Log in as `admin@medicare-hms.com` / `Admin@12345` | Lands on `/admin/dashboard`, topbar shows Administrator | [ ] |
| 1.2 | Log in as a doctor | Lands on `/doctor/dashboard` | [ ] |
| 1.3 | Register a new patient (name, email, phone, password, confirm) | Auto-login to `/patient/dashboard`, patient ID `PAT-0000xx` shown | [ ] |
| 1.4 | Register with that same email again | "An account with this email already exists" | [ ] |
| 1.5 | Register with `not-an-email` and password `short` | Email and password errors shown, no account created | [ ] |
| 1.6 | Log in with a wrong password | "Invalid email or password" (same message for unknown email) | [ ] |
| 1.7 | While signed in as a patient, open `/admin/dashboard` | 403 page, no admin data | [ ] |
| 1.8 | While signed in as a doctor, open `/patient/records` | 403 page | [ ] |
| 1.9 | Sign out, then open `/patient/appointments` | Redirect to login with `next=/patient/appointments` | [ ] |
| 1.10 | Admin deactivates a doctor, then that doctor tries to log in | "This account has been deactivated..." | [ ] |

## 2. Administrator

| # | Step | Expected | Done |
|---|---|---|---|
| 2.1 | Add a department "Test Unit" | Appears in the list, detail page opens | [ ] |
| 2.2 | Try to add "test unit" again | Duplicate-name error | [ ] |
| 2.3 | Try to retire Cardiology (has active doctors) | Refused: active doctors still work here | [ ] |
| 2.4 | Retire "Test Unit", then reactivate it | Both actions succeed | [ ] |
| 2.5 | Create a doctor with a manual password | Doctor can sign in; profile shows department, fee, room | [ ] |
| 2.6 | Edit that doctor's fee and room | Values updated on the profile | [ ] |
| 2.7 | Deactivate and reactivate the new doctor | Login blocked, then allowed | [ ] |
| 2.8 | Delete the new doctor (no history) | Deleted, redirect to doctor list | [ ] |
| 2.9 | Try to delete a demo doctor with appointments | Refused, doctor remains | [ ] |
| 2.10 | Search patients by name, patient ID and phone | Correct patient listed each time | [ ] |
| 2.11 | Edit a patient's phone/address | Values updated | [ ] |
| 2.12 | Deactivate and reactivate a patient | Login blocked, then allowed; history unchanged | [ ] |
| 2.13 | Filter appointments by status `booked`, by doctor, by date range | Only matching rows; pagination keeps filters | [ ] |
| 2.14 | Set From = next month, To = today | "The end date cannot be before the start date" | [ ] |
| 2.15 | Open an appointment and cancel it with a reason | Status Cancelled, reason shown, slot freed | [ ] |
| 2.16 | Open Treatment records, search a diagnosis, filter by doctor | Matching records only; detail page opens | [ ] |
| 2.17 | Confirm there is no edit control on a treatment record | Read-only banner, no form | [ ] |

## 3. Doctor

| # | Step | Expected | Done |
|---|---|---|---|
| 3.1 | Publish a slot for tomorrow 15:00–16:00 | Slot appears under tomorrow | [ ] |
| 3.2 | Publish an overlapping slot 15:30–16:30 | Refused with the existing slot's time | [ ] |
| 3.3 | Publish a slot 20 days ahead | Refused: seven-day window | [ ] |
| 3.4 | Set end time before start time | Refused | [ ] |
| 3.5 | Edit an unbooked slot's capacity | Saved | [ ] |
| 3.6 | Hide, then show the slot | Status changes; hidden slot disappears from patient view | [ ] |
| 3.7 | Delete an unbooked slot | Removed from the schedule | [ ] |
| 3.8 | Open Appointments → Today / Upcoming / This week / All | Each view lists only the correct subset | [ ] |
| 3.9 | Open a today's appointment, click **Mark as completed** | Status Completed | [ ] |
| 3.10 | Open a future booked appointment | "Cannot be completed yet"; no complete button | [ ] |
| 3.11 | Try to complete an already completed appointment | "This appointment is already completed" | [ ] |
| 3.12 | Cancel a booked appointment with a reason | Status Cancelled, slot released | [ ] |
| 3.13 | Open a completed appointment → **Write record** | Form with diagnosis, prescription, plan, notes, follow-up | [ ] |
| 3.14 | Submit with a 3-character diagnosis | Validation error | [ ] |
| 3.15 | Submit a valid record, then edit it | Same record updated; no duplicate | [ ] |
| 3.16 | Try to open a treatment form for a booked visit by URL | Warning: only completed visits | [ ] |
| 3.17 | My patients → open a patient | Complete history from all doctors, allergies visible | [ ] |
| 3.18 | Open another doctor's patient id by URL | 404 | [ ] |

## 4. Patient

| # | Step | Expected | Done |
|---|---|---|---|
| 4.1 | Find a doctor, filter by specialization and department | Filtered list; profile shows seven days of slots | [ ] |
| 4.2 | Book an open slot | Confirmation page with doctor, date, time, fee | [ ] |
| 4.3 | Try to book the same slot again | "You have already booked this slot" | [ ] |
| 4.4 | With two patients, fill a one-patient slot and book from the other | "This slot is fully booked" | [ ] |
| 4.5 | Reschedule an upcoming appointment | New time shown; old slot reappears for booking | [ ] |
| 4.6 | Cancel an upcoming appointment | Status Cancelled; slot bookable by another patient | [ ] |
| 4.7 | Try to cancel twice | "Only a booked appointment can be cancelled" | [ ] |
| 4.8 | Open Medical records | Own diagnoses and prescriptions only | [ ] |
| 4.9 | Open a record | Diagnosis, prescription, plan, notes, follow-up | [ ] |
| 4.10 | Replace the record id in the URL with another patient's | 404 | [ ] |
| 4.11 | Confirm a completed visit without a record shows "Being written" | Badge shown | [ ] |

## 5. Search and filters

| # | Step | Expected | Done |
|---|---|---|---|
| 5.1 | Admin doctors search by name and specialization | Correct subset | [ ] |
| 5.2 | Admin patients search by partial name, `PAT-000002`, phone digits | Correct patient | [ ] |
| 5.3 | Doctor appointments search by patient name | Only that patient's rows | [ ] |
| 5.4 | Patient doctor search by name and department chip | Correct doctors | [ ] |
| 5.5 | Empty search result | Friendly empty state, not an error | [ ] |

## 6. Form validation and database integrity

| # | Step | Expected | Done |
|---|---|---|---|
| 6.1 | Submit registration with mismatched passwords | "Passwords do not match" | [ ] |
| 6.2 | Submit a doctor with an existing email or licence | Duplicate error | [ ] |
| 6.3 | Submit a patient date of birth in the future | "Date of birth cannot be in the future" | [ ] |
| 6.4 | Submit any POST form without the CSRF token (e.g. delete the hidden input in DevTools) | 400 CSRF error, nothing changes | [ ] |
| 6.5 | Inspect SQLite: `sqlite3 instance/hms.sqlite3 ".indexes appointments"` | `uq_active_doctor_slot`, `uq_active_patient_slot` present | [ ] |
| 6.6 | Inspect a completed treatment row after editing | One row per appointment, `updated_at` changed | [ ] |

## 7. UI and mobile responsiveness

| # | Step | Expected | Done |
|---|---|---|---|
| 7.1 | Resize the browser to 375 px wide on the dashboard | Sidebar hides behind the hamburger; content stacks; no horizontal scroll | [ ] |
| 7.2 | Open the sidebar on mobile and press Escape | Drawer closes | [ ] |
| 7.3 | View tables on a phone width (appointments, patients) | Tables scroll inside their card, page does not overflow | [ ] |
| 7.4 | Check the public landing page on mobile | Navbar collapses, hero and cards stack | [ ] |
| 7.5 | Trigger a cancel action | Confirmation modal appears; Cancel closes it, Confirm submits | [ ] |
| 7.6 | Check flash messages | Appear at the top of the content and auto-dismiss | [ ] |
| 7.7 | Check status badges | Text plus colour for Booked/Completed/Cancelled | [ ] |

## 8. Final regression (fresh database)

| # | Step | Expected | Done |
|---|---|---|---|
| 8.1 | Stop server, delete `instance/hms.sqlite3`, run `flask --app run.py init-db` | Tables created, admin seeded, 8 departments | [ ] |
| 8.2 | Run `python seed_demo.py` twice | Second run adds nothing (idempotent) | [ ] |
| 8.3 | Complete one full journey: register → book → doctor completes → doctor writes record → patient reads record → admin reads record | Every step succeeds | [ ] |
| 8.4 | Restart the server | Data persisted; admin can still log in | [ ] |

## 9. Submission checks

| # | Step | Expected | Done |
|---|---|---|---|
| 9.1 | `pip install -r requirements.txt` in a clean virtual environment | Installs without error | [ ] |
| 9.2 | `.env` removed (or contains no real secret) | App still starts with defaults | [ ] |
| 9.3 | `instance/` excluded from the archive | Archive has no database file | [ ] |
| 9.4 | README instructions followed from scratch by a friend | App runs | [ ] |
| 9.5 | PDF report, screenshots and video placed in the submission folder | Present | [ ] |

## 10. Packaging checklist

1. Ensure `.venv/` is **not** included (it can be hundreds of MB).
2. Ensure `.git/` is excluded unless the college asks for the repository.
3. Ensure `instance/hms.sqlite3` is excluded; the app recreates it.
4. Ensure `.env` is excluded (secrets).
5. Remove `__pycache__/` folders and `*.pyc`.
6. Zip from the project root so `README.md`, `requirements.txt` and `run.py`
   are at the top level of the archive:

```bash
zip -r hospital-management-system.zip . \
  -x ".venv/*" ".git/*" "instance/*" "__pycache__/*" "*/__pycache__/*" "*.pyc" ".env"
```

7. Open the ZIP on another machine (or in a temporary folder), follow the
   README, and confirm the app starts before submitting.
