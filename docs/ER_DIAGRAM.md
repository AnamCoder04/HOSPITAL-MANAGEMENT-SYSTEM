# Entity–Relationship Diagram

Seven tables. Authentication lives in `users`; role-specific data lives in
`doctors` and `patients`, each one-to-one with a user.

```mermaid
erDiagram
    USERS ||--o| DOCTORS : "has doctor profile"
    USERS ||--o| PATIENTS : "has patient profile"
    DEPARTMENTS ||--o{ DOCTORS : "employs"
    DOCTORS ||--o{ DOCTOR_AVAILABILITY : "publishes"
    DOCTORS ||--o{ APPOINTMENTS : "is assigned"
    PATIENTS ||--o{ APPOINTMENTS : "books"
    DOCTOR_AVAILABILITY ||--o{ APPOINTMENTS : "is booked as"
    APPOINTMENTS ||--o| TREATMENTS : "produces"
    DOCTORS ||--o{ TREATMENTS : "writes"

    USERS {
        int id PK
        string full_name
        string email UK
        string password_hash
        string role "admin | doctor | patient"
        string phone
        bool is_active
        bool is_blacklisted
        datetime last_login
        datetime created_at
    }

    DEPARTMENTS {
        int id PK
        string name UK
        text description
        bool is_active
        datetime created_at
    }

    DOCTORS {
        int id PK
        int user_id FK,UK "users.id"
        int department_id FK "departments.id"
        string specialization
        string qualifications
        string license_no UK
        int experience_years
        numeric consultation_fee
        string room_no
        text bio
        bool is_available
    }

    PATIENTS {
        int id PK
        int user_id FK,UK "users.id"
        string patient_code UK "PAT-000001"
        date date_of_birth
        string gender
        string blood_group
        string address
        string emergency_contact
        text allergies
    }

    DOCTOR_AVAILABILITY {
        int id PK
        int doctor_id FK "doctors.id"
        date available_date
        time start_time
        time end_time
        int max_patients
        bool is_active
    }

    APPOINTMENTS {
        int id PK
        int patient_id FK "patients.id"
        int doctor_id FK "doctors.id"
        int availability_id FK "doctor_availability.id, nullable"
        date appointment_date
        time appointment_time
        string status "booked | completed | cancelled"
        text reason
        text cancel_reason
        datetime created_at
    }

    TREATMENTS {
        int id PK
        int appointment_id FK,UK "appointments.id"
        int doctor_id FK "doctors.id"
        text diagnosis
        text prescription
        text treatment_plan
        text notes
        date follow_up_date
        datetime created_at
        datetime updated_at
    }
```

## Relationship rules

| Relationship | Cardinality | Rule |
|---|---|---|
| `users` → `doctors` | 1 : 0..1 | A login has at most one doctor profile (`UNIQUE user_id`) |
| `users` → `patients` | 1 : 0..1 | A login has at most one patient profile; deleting the user cascades to the profile |
| `departments` → `doctors` | 1 : N | `ON DELETE RESTRICT`; departments are retired, never deleted while staffed |
| `doctors` → `doctor_availability` | 1 : N | Doctor-owned; cascades when the doctor is deleted; unique per `(doctor, date, start_time)` |
| `doctors` / `patients` → `appointments` | 1 : N | Every appointment belongs to exactly one doctor and one patient |
| `doctor_availability` → `appointments` | 1 : N | `ON DELETE SET NULL` keeps history if a slot is removed |
| `appointments` → `treatments` | 1 : 0..1 | `UNIQUE appointment_id`; one consultation, one record; record cascades with the appointment |
| `doctors` → `treatments` | 1 : N | Audit trail of who wrote the record |

## Integrity rules enforced by the database

- `CHECK` constraints on `users.role`, `appointments.status`, `patients.gender`,
  availability time order and non-negative fees/experience.
- `uq_doctor_availability_slot`: one slot per doctor, date and start time.
- `uq_active_doctor_slot`: partial unique index on
  `(doctor_id, appointment_date, appointment_time)` where `status != 'cancelled'`
  — no double booking, but cancelled rows release the time.
- `uq_active_patient_slot`: partial unique index on
  `(patient_id, doctor_id, appointment_date, appointment_time)` — the same
  patient cannot hold two active bookings at the same moment.
- `UNIQUE(email)`, `UNIQUE(license_no)`, `UNIQUE(patient_code)`,
  `UNIQUE(appointment_id)` on treatments.
