"""Patient appointment rules (Task 11).

Listing a patient's own appointments, and cancelling one. Cancelling is a
status change, never a delete: the row stays as history and stops occupying
the doctor's slot because the partial unique index ignores cancelled rows.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased

from app.extensions import db
from app.models import (
    Appointment,
    AppointmentStatus,
    Doctor,
    DoctorAvailability,
    Patient,
    User,
)


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


def reschedule_appointment(patient: Patient, appointment: Appointment, slot: DoctorAvailability) -> Appointment:
    """Move the patient's own booked appointment to another published slot.

    The new slot is re-validated here (active, future, not full, same doctor),
    and the database's unique indexes are still the final guard.
    """
    if appointment.patient_id != patient.id:
        raise PermissionError("This appointment does not belong to you.")
    if appointment.status != AppointmentStatus.BOOKED:
        raise ValueError("Only a booked appointment can be rescheduled.")
    if _starts_at(appointment) <= datetime.now():
        raise ValueError("This appointment has already started and cannot be rescheduled.")

    if slot.doctor_id != appointment.doctor_id:
        raise ValueError("Choose a new time with the same doctor.")
    if slot.id == appointment.availability_id:
        raise ValueError("That is already your appointment time.")
    if not slot.is_active:
        raise ValueError("That slot is no longer open for booking.")
    if slot.available_date < date.today():
        raise ValueError("That slot has already passed.")
    if slot.is_full:
        raise ValueError("That slot is fully booked. Please choose another time.")

    duplicate = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.availability_id == slot.id,
        Appointment.status != AppointmentStatus.CANCELLED,
        Appointment.id != appointment.id,
    ).first()
    if duplicate is not None:
        raise ValueError("You already have another appointment in that slot.")

    # Spread patients inside a multi-patient slot exactly like a new booking.
    minutes = int(
        (
            datetime.combine(date.min, slot.end_time)
            - datetime.combine(date.min, slot.start_time)
        ).total_seconds()
        // 60
    )
    step = max(minutes // slot.max_patients, 1)
    new_time = (
        datetime.combine(slot.available_date, slot.start_time)
        + timedelta(minutes=step * slot.booked_count)
    ).time()

    appointment.availability = slot
    appointment.appointment_date = slot.available_date
    appointment.appointment_time = new_time

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ValueError("That time was just taken. Please choose another slot.")

    return appointment


# ---------------------------------------------------------------------------
# Staff-side management
# ---------------------------------------------------------------------------
def search_appointments(
    q: str = "",
    doctor_id: int = 0,
    patient_id: int = 0,
    status: str = "",
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    per_page: int = 10,
):
    """Administrator list: search text, doctor, patient, status and date range."""
    patient_user = aliased(User)
    doctor_user = aliased(User)

    query = (
        Appointment.query
        .join(Patient, Appointment.patient_id == Patient.id)
        .join(patient_user, Patient.user_id == patient_user.id)
        .join(Doctor, Appointment.doctor_id == Doctor.id)
        .join(doctor_user, Doctor.user_id == doctor_user.id)
    )

    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            or_(patient_user.full_name.ilike(like), doctor_user.full_name.ilike(like))
        )
    if doctor_id:
        query = query.filter(Appointment.doctor_id == doctor_id)
    if patient_id:
        query = query.filter(Appointment.patient_id == patient_id)
    if status in AppointmentStatus.ALL:
        query = query.filter(Appointment.status == status)
    if date_from is not None:
        query = query.filter(Appointment.appointment_date >= date_from)
    if date_to is not None:
        query = query.filter(Appointment.appointment_date <= date_to)

    return query.order_by(
        Appointment.appointment_date.desc(),
        Appointment.appointment_time.desc(),
    ).paginate(page=max(page, 1), per_page=per_page, error_out=False)


def doctor_appointments(
    doctor: Doctor, view: str = "upcoming", status: str = "", q: str = ""
) -> list[Appointment]:
    """One doctor's appointments, filtered by view/status/patient name."""
    query = Appointment.query.filter(Appointment.doctor_id == doctor.id)
    today = date.today()

    if view == "today":
        query = query.filter(Appointment.appointment_date == today)
    elif view == "week":
        query = query.filter(
            Appointment.appointment_date >= today,
            Appointment.appointment_date <= today + timedelta(days=6),
        )
    elif view == "upcoming":
        query = query.filter(
            Appointment.status == AppointmentStatus.BOOKED,
            Appointment.appointment_date >= today,
        )

    if status in AppointmentStatus.ALL:
        query = query.filter(Appointment.status == status)

    if q:
        query = query.join(Patient, Appointment.patient_id == Patient.id).join(
            User, Patient.user_id == User.id
        ).filter(User.full_name.ilike(f"%{q.strip()}%") )

    if view in ("today", "upcoming", "week"):
        query = query.order_by(Appointment.appointment_date, Appointment.appointment_time)
    else:
        query = query.order_by(
            Appointment.appointment_date.desc(), Appointment.appointment_time.desc()
        )

    return query.all()


def doctor_appointment_counts(doctor: Doctor) -> dict:
    """Counts for the doctor's list tabs."""
    today = date.today()
    base = Appointment.query.filter_by(doctor_id=doctor.id)

    return {
        "today": base.filter_by(appointment_date=today).count(),
        "upcoming": base.filter(
            Appointment.status == AppointmentStatus.BOOKED,
            Appointment.appointment_date >= today,
        ).count(),
        "week": base.filter(
            Appointment.appointment_date >= today,
            Appointment.appointment_date <= today + timedelta(days=6),
        ).count(),
        "all": base.count(),
    }


def complete_appointment(doctor: Doctor, appointment: Appointment) -> Appointment:
    """Mark the doctor's own booked appointment as completed."""
    if appointment.doctor_id != doctor.id:
        raise PermissionError("This appointment is not assigned to you.")
    if appointment.status == AppointmentStatus.COMPLETED:
        raise ValueError("This appointment is already completed.")
    if appointment.status != AppointmentStatus.BOOKED:
        raise ValueError("A cancelled appointment cannot be completed.")
    if appointment.appointment_date > date.today():
        raise ValueError("This appointment is in the future and cannot be completed yet.")

    appointment.status = AppointmentStatus.COMPLETED
    db.session.commit()
    return appointment


def cancel_by_doctor(doctor: Doctor, appointment: Appointment, reason: str = "") -> Appointment:
    """Cancel the doctor's own booked appointment."""
    if appointment.doctor_id != doctor.id:
        raise PermissionError("This appointment is not assigned to you.")
    if appointment.status != AppointmentStatus.BOOKED:
        raise ValueError("Only a booked appointment can be cancelled.")

    appointment.status = AppointmentStatus.CANCELLED
    appointment.cancel_reason = (reason or "").strip() or "Cancelled by the doctor."
    db.session.commit()
    return appointment


def cancel_by_admin(appointment: Appointment, reason: str = "") -> Appointment:
    """Cancel any booked appointment on the administrator's authority."""
    if appointment.status != AppointmentStatus.BOOKED:
        raise ValueError("Only a booked appointment can be cancelled.")

    appointment.status = AppointmentStatus.CANCELLED
    appointment.cancel_reason = (reason or "").strip() or "Cancelled by the administrator."
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
