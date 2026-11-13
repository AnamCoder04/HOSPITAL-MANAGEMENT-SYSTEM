"""Patient routes.

Task 11: doctor search (name, specialization, department), doctor profiles
with seven-day availability, slot booking with a confirmation page, and the
patient's own appointment list with cancellation.

Every booking is made against a published slot id - the date and time are
read from the slot, never from the request - so a patient cannot create an
appointment the doctor never offered.
"""

from __future__ import annotations

from datetime import date

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.blueprints.patient import patient_bp
from app.blueprints.patient.forms import DoctorSearchForm, RescheduleForm
from app.extensions import db
from app.models import Appointment, AppointmentStatus, Doctor, DoctorAvailability, Role
from app.services import appointment_service, availability_service, treatment_service
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
# Doctor search and availability
# ---------------------------------------------------------------------------
@patient_bp.route("/doctors")
@role_required(Role.PATIENT)
def doctors():
    """Search doctors by name, specialization and department."""
    form = DoctorSearchForm(request.args)
    form.validate()  # GET form: invalid choices show an error instead of filtering silently

    doctors_list = availability_service.bookable_doctors(
        name=form.name.data or "",
        specialization="" if form.specialization.errors else (form.specialization.data or ""),
        department_id=0 if form.department_id.errors else (form.department_id.data or 0),
    )

    return render_template(
        "patient/doctors.html",
        form=form,
        doctors=doctors_list,
        departments=availability_service.department_options(),
        department_counts=availability_service.doctor_count_by_department(),
        open_slots={
            doctor.id: availability_service.open_slot_count(doctor)
            for doctor in doctors_list
        },
        filtered=bool(form.name.data or form.specialization.data or form.department_id.data),
        today=date.today(),
    )


@patient_bp.route("/doctors/<int:doctor_id>")
@role_required(Role.PATIENT)
def doctor_view(doctor_id: int):
    """One doctor's profile and published slots for the next seven days."""
    patient = _current_patient()
    if patient is None:
        return redirect(url_for("main.index"))

    doctor = db.get_or_404(Doctor, doctor_id)
    slots_by_date = availability_service.patient_slots_by_date(doctor)
    all_slots = [slot for slots in slots_by_date.values() for slot in slots]

    # Slots this patient already holds, so the button can say "Booked".
    my_slot_ids = {
        appointment.availability_id
        for appointment in Appointment.query.filter(
            Appointment.patient_id == patient.id,
            Appointment.availability_id.isnot(None),
            Appointment.status != AppointmentStatus.CANCELLED,
        ).all()
    }

    return render_template(
        "patient/doctor_view.html",
        doctor=doctor,
        days=availability_service.week_dates(),
        slots_by_date=slots_by_date,
        statuses=availability_service.statuses_for(all_slots),
        status_meta=availability_service.STATUS_META,
        open_slots=availability_service.open_slot_count(doctor),
        my_slot_ids=my_slot_ids,
        today=date.today(),
    )


# ---------------------------------------------------------------------------
# Booking
# ---------------------------------------------------------------------------
@patient_bp.route("/book/<int:slot_id>", methods=["POST"])
@role_required(Role.PATIENT)
def book_slot(slot_id: int):
    """Book a published slot (date and time come from the slot itself)."""
    patient = _current_patient()
    if patient is None:
        return redirect(url_for("main.index"))

    slot = db.get_or_404(DoctorAvailability, slot_id)

    try:
        appointment = availability_service.book_slot(patient, slot)
    except ValueError as error:
        flash(str(error), "warning")
        return redirect(url_for("patient.doctor_view", doctor_id=slot.doctor_id))

    flash("Your appointment is confirmed.", "success")
    return redirect(url_for("patient.booking_confirmation", appointment_id=appointment.id))


@patient_bp.route("/appointments/<int:appointment_id>/confirmation")
@role_required(Role.PATIENT)
def booking_confirmation(appointment_id: int):
    """Booking confirmation for the patient's own appointment."""
    patient = _current_patient()
    if patient is None:
        return redirect(url_for("main.index"))

    appointment = Appointment.query.filter_by(
        id=appointment_id, patient_id=patient.id
    ).first_or_404()

    return render_template(
        "patient/booking_confirmation.html",
        appointment=appointment,
        patient=patient,
        today=date.today(),
    )


# ---------------------------------------------------------------------------
# My appointments
# ---------------------------------------------------------------------------
@patient_bp.route("/appointments")
@role_required(Role.PATIENT)
def appointments():
    """Upcoming appointments plus the full history."""
    patient = _current_patient()
    if patient is None:
        return redirect(url_for("main.index"))

    return render_template(
        "patient/appointments.html",
        patient=patient,
        upcoming=appointment_service.upcoming_appointments(patient),
        history=appointment_service.past_appointments(patient),
        counts=appointment_service.appointment_counts(patient),
        today=date.today(),
    )


@patient_bp.route("/records")
@role_required(Role.PATIENT)
def records():
    """The patient's own medical history: completed visits and their records."""
    patient = _current_patient()
    if patient is None:
        return redirect(url_for("main.index"))

    return render_template(
        "patient/records.html",
        patient=patient,
        records=treatment_service.patient_history(patient),
        completed=treatment_service.patient_completed_visits(patient),
        summary=treatment_service.medical_history_summary(patient),
        today=date.today(),
    )


@patient_bp.route("/records/<int:treatment_id>")
@role_required(Role.PATIENT)
def record_view(treatment_id: int):
    """One of this patient's own clinical records."""
    patient = _current_patient()
    if patient is None:
        return redirect(url_for("main.index"))

    treatment = treatment_service.patient_treatment(patient, treatment_id)
    if treatment is None:
        # Another patient's record must not be distinguishable from a missing one.
        return ("Not found", 404)

    return render_template(
        "patient/record_view.html",
        patient=patient,
        treatment=treatment,
        appointment=treatment.appointment,
    )


@patient_bp.route("/appointments/<int:appointment_id>/reschedule", methods=["GET", "POST"])
@role_required(Role.PATIENT)
def reschedule_appointment(appointment_id: int):
    """Move a booked appointment to another open slot with the same doctor."""
    patient = _current_patient()
    if patient is None:
        return redirect(url_for("main.index"))

    appointment = appointment_service.patient_appointment(patient, appointment_id)
    if appointment is None:
        return ("Not found", 404)

    if appointment.status != AppointmentStatus.BOOKED:
        flash("Only a booked appointment can be rescheduled.", "warning")
        return redirect(url_for("patient.appointments"))
    if not appointment_service.can_cancel(appointment):
        flash("This appointment has already started and cannot be rescheduled.", "warning")
        return redirect(url_for("patient.appointments"))

    # Only slots the doctor still offers, excluding the current one.
    grouped = availability_service.patient_slots_by_date(appointment.doctor)
    slots = [
        slot
        for day_slots in grouped.values()
        for slot in day_slots
        if slot.id != appointment.availability_id and not slot.is_full
    ]

    form = RescheduleForm()
    form.slot_id.choices = [
        (
            slot.id,
            f"{slot.available_date.strftime('%a, %d %b')} at {slot.label} "
            f"({slot.slots_left} place{'s' if slot.slots_left != 1 else ''} left)",
        )
        for slot in slots
    ]

    if form.validate_on_submit():
        slot = next((item for item in slots if item.id == form.slot_id.data), None)
        if slot is None:
            flash("Choose one of the offered times.", "warning")
        else:
            try:
                appointment_service.reschedule_appointment(patient, appointment, slot)
            except ValueError as error:
                flash(str(error), "warning")
            else:
                flash(
                    "Appointment moved to "
                    f"{appointment.appointment_date.strftime('%a, %d %b')} at "
                    f"{appointment.appointment_time.strftime('%H:%M')}.",
                    "success",
                )
                return redirect(
                    url_for("patient.booking_confirmation", appointment_id=appointment.id)
                )

    return render_template(
        "patient/reschedule.html",
        appointment=appointment,
        form=form,
        slots=slots,
        today=date.today(),
    )


@patient_bp.route("/appointments/<int:appointment_id>/cancel", methods=["POST"])
@role_required(Role.PATIENT)
def cancel_appointment(appointment_id: int):
    """Cancel one of this patient's own booked appointments."""
    patient = _current_patient()
    if patient is None:
        return redirect(url_for("main.index"))

    appointment = appointment_service.patient_appointment(patient, appointment_id)
    if appointment is None:
        # Not this patient's appointment: behave as if it does not exist.
        return ("Not found", 404)

    try:
        appointment_service.cancel_appointment(patient, appointment)
    except ValueError as error:
        flash(str(error), "warning")
    else:
        flash(
            f"Appointment with Dr. {appointment.doctor.full_name} on "
            f"{appointment.appointment_date.strftime('%d %b')} at "
            f"{appointment.appointment_time.strftime('%H:%M')} was cancelled. "
            "The slot is free for other patients.",
            "success",
        )

    return redirect(url_for("patient.appointments"))
