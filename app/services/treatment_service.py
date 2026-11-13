"""Treatment and medical-history rules (Task 13).

A treatment record belongs to exactly one appointment (UNIQUE appointment_id)
and is written by the doctor that appointment is assigned to. The rules kept
here are the ones a template must not be trusted with:

* only the assigned doctor can create or update a record;
* only a completed visit can carry a record;
* follow-up dates cannot lie before the visit;
* a doctor sees only patients they have actually seen;
* a patient sees only their own records;
* the administrator can read every record but never edits one.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import case, func, or_
from sqlalchemy.orm import aliased

from app.extensions import db
from app.models import (
    Appointment,
    AppointmentStatus,
    Doctor,
    Patient,
    Treatment,
    User,
)


# ---------------------------------------------------------------------------
# Doctor: assigned patients and their history
# ---------------------------------------------------------------------------
def assigned_patients(doctor: Doctor, q: str = "") -> list[dict]:
    """Patients who have at least one appointment with this doctor.

    Grouped in SQL so the list stays correct regardless of how many visits a
    patient has. `q` searches the patient's name only.
    """
    last_visit = func.max(Appointment.appointment_date)
    completed = func.sum(
        case((Appointment.status == AppointmentStatus.COMPLETED, 1), else_=0)
    )

    query = (
        db.session.query(Patient, func.count(Appointment.id), completed, last_visit)
        .join(Appointment, Appointment.patient_id == Patient.id)
        .join(User, Patient.user_id == User.id)
        .filter(Appointment.doctor_id == doctor.id)
    )

    if q and q.strip():
        query = query.filter(User.full_name.ilike(f"%{q.strip()}%"))

    rows = (
        query.group_by(Patient.id)
        .order_by(last_visit.desc(), User.full_name)
        .all()
    )

    return [
        {
            "patient": patient,
            "visits": visits or 0,
            "completed": int(completed_visits or 0),
            "last_visit": latest,
        }
        for patient, visits, completed_visits, latest in rows
    ]


def doctor_patient(doctor: Doctor, patient_id: int) -> Patient | None:
    """The patient, but only if this doctor has seen them at least once."""
    return (
        Patient.query.filter(
            Patient.id == patient_id,
            Patient.appointments.any(Appointment.doctor_id == doctor.id),
        ).first()
    )


def doctor_appointments_for(doctor: Doctor, patient: Patient) -> list[Appointment]:
    """This doctor's own visits with one patient, newest first."""
    return (
        Appointment.query.filter_by(doctor_id=doctor.id, patient_id=patient.id)
        .order_by(
            Appointment.appointment_date.desc(),
            Appointment.appointment_time.desc(),
        )
        .all()
    )


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------
def patient_history(patient: Patient) -> list[Treatment]:
    """Every clinical record for a patient, newest visit first."""
    return (
        Treatment.query.join(Treatment.appointment)
        .filter(Appointment.patient_id == patient.id)
        .order_by(
            Appointment.appointment_date.desc(),
            Appointment.appointment_time.desc(),
        )
        .all()
    )


def patient_completed_visits(patient: Patient) -> list[Appointment]:
    """Completed appointments of a patient, newest first, with their record."""
    return (
        Appointment.query.filter_by(
            patient_id=patient.id, status=AppointmentStatus.COMPLETED
        )
        .order_by(
            Appointment.appointment_date.desc(),
            Appointment.appointment_time.desc(),
        )
        .all()
    )


def patient_treatment(patient: Patient, treatment_id: int) -> Treatment | None:
    """One record, scoped to this patient. Another patient's id returns None."""
    return (
        Treatment.query.join(Treatment.appointment)
        .filter(
            Treatment.id == treatment_id,
            Appointment.patient_id == patient.id,
        )
        .first()
    )


def save_treatment(doctor: Doctor, appointment: Appointment, form) -> Treatment:
    """Create or update the record for one completed visit.

    The appointment is re-checked here even though the route already scoped
    the lookup: this function is the single place the rules live, and it is
    what the verification script exercises directly.
    """
    if appointment.doctor_id != doctor.id:
        raise PermissionError("This appointment is not assigned to you.")
    if appointment.status != AppointmentStatus.COMPLETED:
        raise ValueError(
            "Treatment details can only be recorded for a completed visit. "
            "Mark the appointment completed first."
        )

    diagnosis = (form.diagnosis.data or "").strip()
    if len(diagnosis) < 5:
        raise ValueError("Enter a diagnosis of at least 5 characters.")

    follow_up = form.follow_up_date.data
    if follow_up is not None and follow_up < appointment.appointment_date:
        raise ValueError("The follow-up date cannot be before the visit date.")

    treatment = appointment.treatment
    if treatment is None:
        treatment = Treatment(appointment_id=appointment.id, doctor_id=doctor.id)
        db.session.add(treatment)

    treatment.diagnosis = diagnosis
    treatment.prescription = (form.prescription.data or "").strip() or None
    treatment.treatment_plan = (form.treatment_plan.data or "").strip() or None
    treatment.notes = (form.notes.data or "").strip() or None
    treatment.follow_up_date = follow_up

    db.session.commit()
    return treatment


def medical_history_summary(patient: Patient) -> dict:
    """Counts and alarms for the record header."""
    records = patient_history(patient)
    return {
        "records": len(records),
        "prescriptions": sum(1 for record in records if record.prescription),
        "follow_ups": sum(1 for record in records if record.follow_up_date),
        "doctors": len({record.doctor_id for record in records}),
        "last_record": records[0] if records else None,
        "completed_visits": Appointment.query.filter_by(
            patient_id=patient.id, status=AppointmentStatus.COMPLETED
        ).count(),
    }


# ---------------------------------------------------------------------------
# Administrator: read-only access to every record
# ---------------------------------------------------------------------------
def search_treatments(
    q: str = "",
    doctor_id: int = 0,
    patient_id: int = 0,
    page: int = 1,
    per_page: int = 10,
):
    """Paginated treatment records with search and doctor/patient filters."""
    patient_user = aliased(User)
    doctor_user = aliased(User)

    query = (
        Treatment.query.join(Treatment.appointment)
        .join(Patient, Appointment.patient_id == Patient.id)
        .join(patient_user, Patient.user_id == patient_user.id)
        .join(Doctor, Appointment.doctor_id == Doctor.id)
        .join(doctor_user, Doctor.user_id == doctor_user.id)
    )

    if q and q.strip():
        like = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Treatment.diagnosis.ilike(like),
                Treatment.prescription.ilike(like),
                patient_user.full_name.ilike(like),
                doctor_user.full_name.ilike(like),
            )
        )
    if doctor_id:
        query = query.filter(Appointment.doctor_id == doctor_id)
    if patient_id:
        query = query.filter(Appointment.patient_id == patient_id)

    return query.order_by(
        Appointment.appointment_date.desc(),
        Appointment.appointment_time.desc(),
    ).paginate(page=max(page, 1), per_page=per_page, error_out=False)


def treatment_options() -> dict:
    """Choices for the administrator's doctor and patient filters."""
    return {
        "doctors": [
            (doctor.id, f"Dr. {doctor.full_name}")
            for doctor in Doctor.query.join(Doctor.user).order_by(User.full_name).all()
        ],
        "patients": [
            (patient.id, f"{patient.full_name} ({patient.patient_code})")
            for patient in Patient.query.join(Patient.user).order_by(User.full_name).all()
        ],
    }
