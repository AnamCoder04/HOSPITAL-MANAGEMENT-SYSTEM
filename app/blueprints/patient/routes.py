"""Patient routes.

Dashboard (Task 5), a read-only view of doctors' published availability
(Task 10) and booking a published slot.

Booking always takes a slot id: the date and time come from the slot itself,
so a patient cannot book a time the doctor never published.
"""

from __future__ import annotations

from datetime import date

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.blueprints.patient import patient_bp
from app.extensions import db
from app.models import Doctor, DoctorAvailability, Role
from app.services import availability_service
from app.services.stats_service import patient_dashboard_stats, upcoming_appointments_for_patient
from app.utils.decorators import role_required


def _current_patient():
    patient = current_user.patient
    if patient is None:
        flash("Your patient profile is not set up yet. Please contact the hospital.", "warning")
    return patient


@patient_bp.route("/dashboard")
@role_required(Role.PATIENT)
def dashboard():
    """This patient's own overview: next visit, counts and upcoming list."""
    patient = _current_patient()
    if patient is None:
        return redirect(url_for("main.index"))

    upcoming = upcoming_appointments_for_patient(patient)

    return render_template(
        "patient/dashboard.html",
        patient=patient,
        stats=patient_dashboard_stats(patient),
        upcoming_appointments=upcoming,
        next_appointment=upcoming[0] if upcoming else None,
        today=date.today(),
    )


# ---------------------------------------------------------------------------
# Doctors and availability
# ---------------------------------------------------------------------------
@patient_bp.route("/doctors")
@role_required(Role.PATIENT)
def doctors():
    """Doctors accepting bookings, with a live count of open slots."""
    term = (request.args.get("q") or "").strip()[:80]
    doctors_list = availability_service.bookable_doctors(term)

    return render_template(
        "patient/doctors.html",
        doctors=doctors_list,
        open_slots={
            doctor.id: availability_service.open_slot_count(doctor)
            for doctor in doctors_list
        },
        term=term,
        today=date.today(),
    )


@patient_bp.route("/doctors/<int:doctor_id>")
@role_required(Role.PATIENT)
def doctor_view(doctor_id: int):
    """One doctor's published slots for the next seven days."""
    doctor = db.get_or_404(Doctor, doctor_id)
    slots_by_date = availability_service.patient_slots_by_date(doctor)
    all_slots = [slot for slots in slots_by_date.values() for slot in slots]

    return render_template(
        "patient/doctor_view.html",
        doctor=doctor,
        days=availability_service.week_dates(),
        slots_by_date=slots_by_date,
        statuses=availability_service.statuses_for(all_slots),
        status_meta=availability_service.STATUS_META,
        today=date.today(),
    )


@patient_bp.route("/book/<int:slot_id>", methods=["POST"])
@role_required(Role.PATIENT)
def book_slot(slot_id: int):
    """Book a published slot (date and time are taken from the slot)."""
    patient = _current_patient()
    if patient is None:
        return redirect(url_for("main.index"))

    slot = db.get_or_404(DoctorAvailability, slot_id)

    try:
        appointment = availability_service.book_slot(patient, slot)
    except ValueError as error:
        flash(str(error), "warning")
    else:
        flash(
            f"Booked with Dr. {appointment.doctor.full_name} on "
            f"{appointment.appointment_date.strftime('%A, %d %b')} at "
            f"{appointment.appointment_time.strftime('%H:%M')}.",
            "success",
        )
        return redirect(url_for("patient.dashboard"))

    return redirect(url_for("patient.doctor_view", doctor_id=slot.doctor_id))
