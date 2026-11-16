# Endpoint documentation

The application is server-rendered (Jinja2), so most endpoints return HTML
pages rather than JSON. Every state-changing request is a **POST** protected by
a CSRF token (`csrf_token` form field) and is answered with a `302` redirect
plus a flash message.

- **Access**: `Public`, `Admin`, `Doctor`, `Patient` (enforced by
  `@role_required`). Wrong role → `403`; signed out → `302` to
  `/auth/login?next=...`.
- Records belonging to someone else return **404**, never 403, so ids cannot be
  probed.

## Public

| Method | Path | Access | Parameters | Response |
|---|---|---|---|---|
| GET | `/` | Public | — | Landing page with features and call-to-action |
| GET/POST | `/auth/login` | Public | `email`, `password`, `remember` | 302 to the role dashboard on success; 200 with errors otherwise |
| GET/POST | `/auth/register` | Public | `full_name`, `email`, `phone`, `password`, `confirm_password` | 302 to `/patient/dashboard`; 200 with field errors otherwise |
| POST | `/auth/logout` | Any signed-in | — | 302 to `/auth/login` |
| GET | `/static/<path>` | Public | — | CSS, JS, images |

Login and registration POSTs accept optional `next` in the query string; only
same-host targets are followed.

## Administrator (`/admin/*`)

| Method | Path | Parameters | Purpose |
|---|---|---|---|
| GET | `/admin/dashboard` | — | Totals, status chart, recent activity |
| GET | `/admin/doctors` | `q`, `specialization` | Doctor list with search |
| GET/POST | `/admin/doctors/new` | doctor fields, `password_mode`, `password`, `confirm_password` | Create doctor + login |
| GET | `/admin/doctors/<id>` | — | Doctor profile, stats, guarded delete |
| GET/POST | `/admin/doctors/<id>/edit` | doctor fields | Update doctor + account |
| POST | `/admin/doctors/<id>/toggle` | — | Activate/deactivate login |
| POST | `/admin/doctors/<id>/delete` | — | Delete only when no appointment/treatment history |
| GET | `/admin/patients` | `q`, `patient_id`, `phone`, `page` | Paginated patient search |
| GET | `/admin/patients/<id>` | `page` | Profile, appointment + treatment history |
| GET/POST | `/admin/patients/<id>/edit` | patient profile fields | Update contact/medical profile |
| POST | `/admin/patients/<id>/toggle` | — | Deactivate/reactivate login |
| GET | `/admin/departments` | `q`, `status` (`all`/`active`/`inactive`) | Department list |
| GET/POST | `/admin/departments/new` | `name`, `description`, `is_active` | Create department |
| GET | `/admin/departments/<id>` | — | Department details and roster |
| GET/POST | `/admin/departments/<id>/edit` | department fields | Rename/describe/retire |
| POST | `/admin/departments/<id>/toggle` | — | Retire/reactivate (refused while staffed) |
| GET | `/admin/appointments` | `q`, `doctor_id`, `patient_id`, `status`, `date_from`, `date_to`, `page` | Filtered appointment list |
| GET | `/admin/appointments/<id>` | — | Appointment details |
| POST | `/admin/appointments/<id>/cancel` | `reason` (optional) | Cancel a booked appointment |
| GET | `/admin/treatments` | `q`, `doctor_id`, `patient_id`, `page` | All clinical records (read-only) |
| GET | `/admin/treatments/<id>` | — | One record; no edit routes exist (POST → 405) |

## Doctor (`/doctor/*`)

| Method | Path | Parameters | Purpose |
|---|---|---|---|
| GET | `/doctor/dashboard` | — | Today's schedule and counts |
| GET | `/doctor/appointments` | `view` (`upcoming`/`today`/`week`/`all`), `status`, `q` | Own appointment list |
| GET | `/doctor/appointments/<id>` | — | Appointment details (scoped to the doctor) |
| POST | `/doctor/appointments/<id>/complete` | — | Mark booked appointment completed (today or earlier) |
| POST | `/doctor/appointments/<id>/cancel` | `reason` (optional) | Cancel a booked appointment |
| GET/POST | `/doctor/appointments/<id>/treatment` | `diagnosis`, `prescription`, `treatment_plan`, `notes`, `follow_up_date` | Write/update the record for a completed visit |
| GET/POST | `/doctor/availability` | `available_date`, `start_time`, `end_time`, `max_patients` | Publish a slot |
| GET/POST | `/doctor/availability/<slot_id>/edit` | same slot fields | Edit own slot |
| POST | `/doctor/availability/<slot_id>/toggle` | — | Hide/show own slot |
| POST | `/doctor/availability/<slot_id>/delete` | — | Delete own unbooked slot |
| GET | `/doctor/patients` | `q` | Patients seen through appointments |
| GET | `/doctor/patients/<patient_id>` | — | Patient profile + complete history |
| GET | `/doctor/profile` | — | Own professional profile (read-only) |

## Patient (`/patient/*`)

| Method | Path | Parameters | Purpose |
|---|---|---|---|
| GET | `/patient/dashboard` | — | Next visit and counts |
| GET | `/patient/doctors` | `name`, `specialization`, `department_id` | Search bookable doctors |
| GET | `/patient/doctors/<doctor_id>` | — | Doctor profile + 7-day slots |
| POST | `/patient/book/<slot_id>` | `reason` (optional) | Book a published slot |
| GET | `/patient/appointments` | — | Upcoming and past appointments |
| GET | `/patient/appointments/<id>/confirmation` | — | Booking confirmation |
| GET/POST | `/patient/appointments/<id>/reschedule` | `slot_id` | Move to another open slot |
| POST | `/patient/appointments/<id>/cancel` | — | Cancel own booked appointment |
| GET | `/patient/records` | — | Own medical history and completed visits |
| GET | `/patient/records/<treatment_id>` | — | Own clinical record |
| GET | `/patient/profile` | — | Own account/medical profile (read-only) |

## Error responses

| Status | When |
|---|---|
| 302 | Not signed in (to `/auth/login?next=...`) or successful POST redirect |
| 403 | Signed in with the wrong role; rendered `errors/403.html` |
| 404 | Unknown id, or a record that belongs to another user |
| 405 | POST to a GET-only page (e.g. `/admin/treatments/<id>`) |
| 400 | Missing/invalid CSRF token on a POST |

## Booking rules that affect clients

- The booking POST takes **only** `slot_id`; the date and time always come from
  the slot, so a crafted request cannot invent a time.
- A slot can be booked at most `max_patients` times; cancelled appointments do
  not count.
- The same patient cannot book the same slot twice while an appointment there is
  active.
- A completed appointment cannot be cancelled, rescheduled, completed again or
  re-booked at the same moment.
- Treatment records are accepted only for appointments whose status is
  `completed`, and only from the doctor assigned to that appointment.
