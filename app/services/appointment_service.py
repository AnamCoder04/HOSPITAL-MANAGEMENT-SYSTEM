"""Patient appointment rules (Task 11).

Listing a patient's own appointments, and cancelling one. Cancelling is a
status change, never a delete: the row stays as history and stops occupying
the doctor's slot because the partial unique index ignores cancelled rows.
"""

from __future__ import annotations

from datetime import date, datetime

from app.extensions import db
from app.models import Appointment, AppointmentStatus, Patient


def _starts_at(appointment: Appointment) -> datetime:
    return datetime.combine(appointment.appointment_date, appointment.appointment_time)


def patient_appointment(patient: Patient, appointment_id: int) -> Appointment | None:
    """One appointment, only if it belongs to this patient."""
    return Appointment.query.filter_by(id=appointment_id, patient_id=patient.id).first()


def upcoming_appointments(patient: Patient) -> list[Appointment]:
    """Booked appointments that have not started yet, soonest first."""
    now = datetime.now()
    rows = (
        Appointment.query.filter(
            Appointment.patient_id == patient.id,
            Appointment.status == AppointmentStatus.BOOKED,
        )
        .order_by(Appointment.appointment_date, Appointment.appointment_time)
        .all()
    )
    return [appointment for appointment in rows if _starts_at(appointment) > now]


def past_appointments(patient: Patient) -> list[Appointment]:
    """Completed, cancelled and already-started appointments, newest first."""
    upcoming_ids = {appointment.id for appointment in upcoming_appointments(patient)}
    rows = (
        Appointment.query.filter(Appointment.patient_id == patient.id)
        .order_by(
            Appointment.appointment_date.desc(),
            Appointment.appointment_time.desc(),
        )
        .all()
    )
    return [appointment for appointment in rows if appointment.id not in upcoming_ids]


def can_cancel(appointment: Appointment) -> bool:
    """Only a booked appointment that has not started can be cancelled."""
    return (
        appointment.status == AppointmentStatus.BOOKED
        and _starts_at(appointment) > datetime.now()
    )


def cancel_appointment(
    patient: Patient, appointment: Appointment, reason: str = "Cancelled by the patient."
) -> Appointment:
    """Cancel the patient's own appointment, freeing the slot."""
    if appointment.patient_id != patient.id:
        raise PermissionError("This appointment does not belong to you.")
    if appointment.status != AppointmentStatus.BOOKED:
        raise ValueError("Only a booked appointment can be cancelled.")
    if _starts_at(appointment) <= datetime.now():
        raise ValueError("This appointment has already started and can no longer be cancelled.")

    appointment.status = AppointmentStatus.CANCELLED
    appointment.cancel_reason = (reason or "").strip() or "Cancelled by the patient."
    db.session.commit()
    return appointment


def appointment_counts(patient: Patient) -> dict:
    """Upcoming / completed / cancelled / total, from one query each."""
    upcoming = upcoming_appointments(patient)
    completed = Appointment.query.filter_by(
        patient_id=patient.id, status=AppointmentStatus.COMPLETED
    ).count()
    cancelled = Appointment.query.filter_by(
        patient_id=patient.id, status=AppointmentStatus.CANCELLED
    ).count()
    return {
        "upcoming": len(upcoming),
        "completed": completed,
        "cancelled": cancelled,
        "total": Appointment.query.filter_by(patient_id=patient.id).count(),
        "today": Appointment.query.filter_by(
            patient_id=patient.id, appointment_date=date.today()
        ).count(),
    }
