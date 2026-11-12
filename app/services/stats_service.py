"""Dashboard aggregates.

Every number shown on a dashboard comes from here, so the views stay thin and
the queries live in one testable place. Nothing is hard-coded: each value is a
SQLAlchemy query against the live SQLite database.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import func

from app.extensions import db
from app.models import Appointment, AppointmentStatus, Doctor, Patient


def admin_dashboard_stats() -> dict:
    """Hospital-wide counts for the administrator dashboard."""
    today = date.today()

    status_counts = dict(
        db.session.query(Appointment.status, func.count(Appointment.id))
        .group_by(Appointment.status)
        .all()
    )

    return {
        "doctors": Doctor.query.count(),
        "available_doctors": Doctor.query.filter_by(is_available=True).count(),
        "patients": Patient.query.count(),
        "appointments": Appointment.query.count(),
        "today": Appointment.query.filter_by(appointment_date=today).count(),
        "booked": status_counts.get(AppointmentStatus.BOOKED, 0),
        "completed": status_counts.get(AppointmentStatus.COMPLETED, 0),
        "cancelled": status_counts.get(AppointmentStatus.CANCELLED, 0),
        # "Upcoming" = still booked and not in the past.
        "upcoming": Appointment.query.filter(
            Appointment.status == AppointmentStatus.BOOKED,
            Appointment.appointment_date >= today,
        ).count(),
    }


def appointment_status_chart(stats: dict) -> dict:
    """Chart.js payload for the appointment-status doughnut."""
    return {
        "labels": ["Booked", "Completed", "Cancelled"],
        "values": [stats["booked"], stats["completed"], stats["cancelled"]],
    }


def recent_patients(limit: int = 5) -> list[Patient]:
    """Newest patient accounts, by registration time."""
    return Patient.query.order_by(Patient.created_at.desc()).limit(limit).all()


def recent_doctors(limit: int = 5) -> list[Doctor]:
    """Newest doctor profiles, by creation time."""
    return Doctor.query.order_by(Doctor.created_at.desc()).limit(limit).all()


def doctor_dashboard_stats(doctor: Doctor) -> dict:
    """Counts for one doctor. Never mixes in another doctor's rows."""
    today = date.today()
    base = Appointment.query.filter_by(doctor_id=doctor.id)

    return {
        "today": base.filter_by(appointment_date=today).count(),
        "upcoming": base.filter(
            Appointment.status == AppointmentStatus.BOOKED,
            Appointment.appointment_date >= today,
        ).count(),
        "completed": base.filter_by(status=AppointmentStatus.COMPLETED).count(),
        "cancelled": base.filter_by(status=AppointmentStatus.CANCELLED).count(),
        "patients": db.session.query(func.count(func.distinct(Appointment.patient_id)))
        .filter(Appointment.doctor_id == doctor.id)
        .scalar()
        or 0,
    }


def patient_dashboard_stats(patient: Patient) -> dict:
    """Counts for one patient only."""
    today = date.today()
    base = Appointment.query.filter_by(patient_id=patient.id)

    return {
        "upcoming": base.filter(
            Appointment.status == AppointmentStatus.BOOKED,
            Appointment.appointment_date >= today,
        ).count(),
        "completed": base.filter_by(status=AppointmentStatus.COMPLETED).count(),
        "cancelled": base.filter_by(status=AppointmentStatus.CANCELLED).count(),
        "total": base.count(),
    }


def todays_appointments_for_doctor(doctor: Doctor, limit: int = 8) -> list[Appointment]:
    """Today's schedule for one doctor, in time order."""
    return (
        Appointment.query.filter_by(doctor_id=doctor.id, appointment_date=date.today())
        .order_by(Appointment.appointment_time)
        .limit(limit)
        .all()
    )


def upcoming_appointments_for_patient(patient: Patient, limit: int = 3) -> list[Appointment]:
    """The patient's next booked visits."""
    return (
        Appointment.query.filter(
            Appointment.patient_id == patient.id,
            Appointment.status == AppointmentStatus.BOOKED,
            Appointment.appointment_date >= date.today(),
        )
        .order_by(Appointment.appointment_date, Appointment.appointment_time)
        .limit(limit)
        .all()
    )
