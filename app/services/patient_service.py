"""Patient management rules (Task 8).

Everything the administrator's patient screens need, kept out of the views so
the queries and the medical-history rules can be tested in one place.

A patient is never deleted: appointments and treatments are part of the
medical record. The only account action is activate / deactivate.
"""

from __future__ import annotations

import re

from sqlalchemy import false

from app.extensions import db
from app.models import Appointment, Patient, Treatment, User

PATIENT_CODE_RE = re.compile(r"^PAT-(\d{1,9})$", re.IGNORECASE)


def normalise_patient_code(raw: str) -> str | None:
    """Accept 'PAT-000123', 'pat-123' or plain '123' and return 'PAT-000123'.

    Returns None when the text is not a patient ID, so the caller can treat
    malformed searches as "no match" instead of silently ignoring the filter.
    """
    value = (raw or "").strip().upper()
    if not value:
        return None

    match = PATIENT_CODE_RE.match(value)
    if match:
        return f"PAT-{int(match.group(1)):06d}"

    if value.isdigit():
        return f"PAT-{int(value):06d}"

    return None


def normalise_phone_query(raw: str) -> str:
    """Reduce typed phone input to the digits stored in users.phone.

    "+91 98765-43210" becomes "9876543210" so a country-code prefix does not
    stop a partial search from matching the stored number.
    """
    digits = re.sub(r"\D", "", raw or "")
    # "+91 98765 43210" and "919876543210" both mean the stored "9876543210".
    if digits.startswith("91") and ((raw or "").strip().startswith("+") or len(digits) >= 12):
        digits = digits[2:]
    return digits


def search_patients(
    name: str = "",
    patient_code: str = "",
    phone: str = "",
    page: int = 1,
    per_page: int = 10,
):
    """Paginated patient list filtered by name, patient ID and/or phone.

    Every filter is applied in SQL; nothing is filtered in Python after the
    query, so the results always reflect the database.
    """
    query = Patient.query.join(Patient.user)

    if name:
        query = query.filter(User.full_name.ilike(f"%{name.strip()}%"))

    if patient_code:
        code = normalise_patient_code(patient_code)
        query = query.filter(Patient.patient_code == code) if code else query.filter(false())

    if phone:
        digits = normalise_phone_query(phone)
        query = query.filter(User.phone.ilike(f"%{digits}%")) if digits else query.filter(false())

    # id is the tie-breaker: equal created_at values (bulk imports) must not
    # shuffle rows between pages.
    return query.order_by(Patient.created_at.desc(), Patient.id.desc()).paginate(
        page=max(page, 1), per_page=per_page, error_out=False
    )


def update_patient(patient: Patient, form) -> Patient:
    """Apply the edit form to the login account and the medical profile."""
    patient.user.full_name = form.full_name.data
    patient.user.email = form.email.data.strip().lower()
    patient.user.phone = form.phone.data or None

    patient.date_of_birth = form.date_of_birth.data
    patient.gender = form.gender.data or None
    patient.blood_group = form.blood_group.data or None
    patient.address = form.address.data or None
    patient.emergency_contact = form.emergency_contact.data or None
    patient.allergies = form.allergies.data or None

    db.session.commit()
    return patient


def toggle_patient_active(patient: Patient) -> bool:
    """Deactivate or reactivate the patient's login. Returns the new state.

    Deactivation only blocks sign-in. Appointments, diagnoses and prescriptions
    stay exactly as they are - history is never removed.
    """
    patient.user.is_active = not patient.user.is_active
    db.session.commit()
    return patient.user.is_active


def appointments_page(patient: Patient, page: int = 1, per_page: int = 10):
    """One page of the patient's appointments, newest first."""
    return (
        Appointment.query.filter_by(patient_id=patient.id)
        .order_by(
            Appointment.appointment_date.desc(),
            Appointment.appointment_time.desc(),
        )
        .paginate(page=max(page, 1), per_page=per_page, error_out=False)
    )


def patient_treatments(patient: Patient) -> list[Treatment]:
    """The patient's clinical records, newest appointment first."""
    return (
        Treatment.query.join(Treatment.appointment)
        .filter(Appointment.patient_id == patient.id)
        .order_by(
            Appointment.appointment_date.desc(),
            Appointment.appointment_time.desc(),
        )
        .all()
    )


def medical_history_summary(patient: Patient) -> dict:
    """Counts shown on the profile, and proof that history is retained."""
    return {
        "appointments": Appointment.query.filter_by(patient_id=patient.id).count(),
        "treatments": Treatment.query.join(Treatment.appointment)
        .filter(Appointment.patient_id == patient.id)
        .count(),
    }
