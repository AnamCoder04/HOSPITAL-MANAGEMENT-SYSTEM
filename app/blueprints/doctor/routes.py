"""Doctor routes.

Dashboard (Task 5) plus availability management (Task 10): a seven-day
schedule where a doctor publishes, edits, hides and removes their own slots.

Ownership is enforced on every write: a slot is looked up by `id` *and*
`doctor_id == current_user.doctor.id`, so one doctor can never see or change
another doctor's availability.
"""

from __future__ import annotations

from datetime import date, datetime, time

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.blueprints.doctor import doctor_bp
from app.blueprints.doctor.forms import (
    AppointmentFilterForm,
    AvailabilityEditForm,
    AvailabilityForm,
    TreatmentForm,
)
from app.extensions import db
from app.models import Appointment, AppointmentStatus, DoctorAvailability, Role
from app.services import appointment_service, availability_service, treatment_service
from app.services.stats_service import doctor_dashboard_stats, todays_appointments_for_doctor
from app.utils.decorators import role_required


def _current_doctor():
    """The signed-in doctor's profile, or None after explaining why not."""
    doctor = current_user.doctor
    if doctor is None:
        flash("Your doctor profile is not set up yet. Please contact the administrator.", "warning")
    return doctor


@doctor_bp.route("/dashboard")
@role_required(Role.DOCTOR)
def dashboard():
    """This doctor's own overview: today's schedule and counts."""
    doctor = _current_doctor()
    if doctor is None:
        return redirect(url_for("main.index"))

    return render_template(
        "doctor/dashboard.html",
        doctor=doctor,
        stats=doctor_dashboard_stats(doctor),
        todays_appointments=todays_appointments_for_doctor(doctor),
        today=date.today(),
    )


# ---------------------------------------------------------------------------
# Appointments
# ---------------------------------------------------------------------------
@doctor_bp.route("/appointments")
@role_required(Role.DOCTOR)
def appointments():
    """The doctor's own appointments: today, upcoming, this week or all."""
    doctor = _current_doctor()
    if doctor is None:
        return redirect(url_for("main.index"))

    form = AppointmentFilterForm(request.args)
    form.validate()

    # Filtering by status only makes sense across all appointments, so that
    # combination defaults to the "all" view instead of hiding every row.
    view = (request.args.get("view") or "") or ("all" if form.status.data else "upcoming")
    if view not in ("today", "upcoming", "week", "all"):
        view = "upcoming"

    appointments_list = appointment_service.doctor_appointments(
        doctor,
        view=view,
        status="" if form.status.errors else (form.status.data or ""),
        q=form.q.data or "",
    )

    return render_template(
        "doctor/appointments.html",
        doctor=doctor,
        form=form,
        view=view,
        appointments=appointments_list,
        counts=appointment_service.doctor_appointment_counts(doctor),
        today=date.today(),
    )


@doctor_bp.route("/appointments/<int:appointment_id>")
@role_required(Role.DOCTOR)
def appointment_view(appointment_id: int):
    """One of this doctor's own appointments."""
    doctor = _current_doctor()
    if doctor is None:
        return redirect(url_for("main.index"))

    appointment = Appointment.query.filter_by(
        id=appointment_id, doctor_id=doctor.id
    ).first_or_404()

    return render_template(
        "doctor/appointment_view.html",
        doctor=doctor,
        appointment=appointment,
        today=date.today(),
        can_complete=(
            appointment.status == AppointmentStatus.BOOKED
            and appointment.appointment_date <= date.today()
        ),
    )


@doctor_bp.route("/appointments/<int:appointment_id>/complete", methods=["POST"])
@role_required(Role.DOCTOR)
def appointment_complete(appointment_id: int):
    """Mark one of this doctor's own booked appointments as completed."""
    doctor = _current_doctor()
    if doctor is None:
        return redirect(url_for("main.index"))

    appointment = Appointment.query.filter_by(
        id=appointment_id, doctor_id=doctor.id
    ).first_or_404()

    try:
        appointment_service.complete_appointment(doctor, appointment)
    except ValueError as error:
        flash(str(error), "warning")
    else:
        flash(
            f"Appointment with {appointment.patient.full_name} was marked completed.",
            "success",
        )

    return redirect(url_for("doctor.appointment_view", appointment_id=appointment.id))


@doctor_bp.route("/appointments/<int:appointment_id>/cancel", methods=["POST"])
@role_required(Role.DOCTOR)
def appointment_cancel(appointment_id: int):
    """Cancel one of this doctor's own booked appointments."""
    doctor = _current_doctor()
    if doctor is None:
        return redirect(url_for("main.index"))

    appointment = Appointment.query.filter_by(
        id=appointment_id, doctor_id=doctor.id
    ).first_or_404()
    reason = (request.form.get("reason") or "").strip()[:255]

    try:
        appointment_service.cancel_by_doctor(doctor, appointment, reason)
    except ValueError as error:
        flash(str(error), "warning")
    else:
        flash(
            f"Appointment with {appointment.patient.full_name} was cancelled. "
            "The slot is free again.",
            "success",
        )

    return redirect(url_for("doctor.appointment_view", appointment_id=appointment.id))


# ---------------------------------------------------------------------------
# Patients and medical history
# ---------------------------------------------------------------------------
@doctor_bp.route("/patients")
@role_required(Role.DOCTOR)
def patients():
    """Patients this doctor has seen, with visit counts."""
    doctor = _current_doctor()
    if doctor is None:
        return redirect(url_for("main.index"))

    q = (request.args.get("q") or "").strip()

    return render_template(
        "doctor/patients.html",
        doctor=doctor,
        rows=treatment_service.assigned_patients(doctor, q=q),
        q=q,
    )


@doctor_bp.route("/patients/<int:patient_id>")
@role_required(Role.DOCTOR)
def patient_view(patient_id: int):
    """One patient's profile and complete clinical history.

    Scoped to patients this doctor has actually seen: another doctor's
    patient simply 404s instead of leaking a medical record.
    """
    doctor = _current_doctor()
    if doctor is None:
        return redirect(url_for("main.index"))

    patient = treatment_service.doctor_patient(doctor, patient_id)
    if patient is None:
        return ("Not found", 404)

    appointments = treatment_service.doctor_appointments_for(doctor, patient)

    return render_template(
        "doctor/patient_view.html",
        doctor=doctor,
        patient=patient,
        appointments=appointments,
        my_visits=len(appointments),
        my_completed=sum(1 for item in appointments if item.is_completed),
        history=treatment_service.patient_history(patient),
        summary=treatment_service.medical_history_summary(patient),
        today=date.today(),
    )


@doctor_bp.route("/appointments/<int:appointment_id>/treatment", methods=["GET", "POST"])
@role_required(Role.DOCTOR)
def treatment_edit(appointment_id: int):
    """Write or revise the record for one completed visit of this doctor."""
    doctor = _current_doctor()
    if doctor is None:
        return redirect(url_for("main.index"))

    appointment = Appointment.query.filter_by(
        id=appointment_id, doctor_id=doctor.id
    ).first_or_404()

    if appointment.status != AppointmentStatus.COMPLETED:
        flash(
            "Treatment details can only be recorded for a completed visit. "
            "Mark the appointment completed first.",
            "warning",
        )
        return redirect(url_for("doctor.appointment_view", appointment_id=appointment.id))

    form = TreatmentForm(obj=appointment.treatment)
    form.follow_up_date.render_kw = {"min": appointment.appointment_date.isoformat()}

    if form.validate_on_submit():
        try:
            treatment_service.save_treatment(doctor, appointment, form)
        except ValueError as error:
            flash(str(error), "warning")
        else:
            flash(
                f"Treatment record for {appointment.patient.full_name}'s visit on "
                f"{appointment.appointment_date.strftime('%d %b %Y')} was saved.",
                "success",
            )
            return redirect(
                url_for("doctor.appointment_view", appointment_id=appointment.id)
            )

    return render_template(
        "doctor/treatment_form.html",
        doctor=doctor,
        appointment=appointment,
        patient=appointment.patient,
        treatment=appointment.treatment,
        form=form,
    )


# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------
@doctor_bp.route("/availability", methods=["GET", "POST"])
@role_required(Role.DOCTOR)
def availability():
    """The next seven days, grouped by day, with a form to publish a slot."""
    doctor = _current_doctor()
    if doctor is None:
        return redirect(url_for("main.index"))

    first_day, last_day = availability_service.window_bounds()
    form = AvailabilityForm()
    form.available_date.render_kw = {
        "min": first_day.isoformat(),
        "max": last_day.isoformat(),
    }

    if form.validate_on_submit():
        try:
            slot = availability_service.create_slot(doctor, form)
        except ValueError as error:
            flash(str(error), "warning")
        else:
            flash(
                f"Slot published for {slot.available_date.strftime('%a, %d %b')} "
                f"at {slot.label}.",
                "success",
            )
            return redirect(url_for("doctor.availability"))
    elif request.method == "GET":
        form.available_date.data = date.today()
        form.start_time.data = time(9, 0)
        form.end_time.data = time(10, 0)
        form.max_patients.data = 1

    slots_by_date = availability_service.slots_by_date(doctor)
    all_slots = [slot for slots in slots_by_date.values() for slot in slots]

    return render_template(
        "doctor/availability.html",
        doctor=doctor,
        form=form,
        days=availability_service.week_dates(),
        slots_by_date=slots_by_date,
        statuses=availability_service.statuses_for(all_slots),
        status_meta=availability_service.STATUS_META,
        first_day=first_day,
        last_day=last_day,
        today=date.today(),
        now=datetime.now(),
    )


@doctor_bp.route("/availability/<int:slot_id>/edit", methods=["GET", "POST"])
@role_required(Role.DOCTOR)
def availability_edit(slot_id: int):
    """Edit one of this doctor's own slots."""
    doctor = _current_doctor()
    if doctor is None:
        return redirect(url_for("main.index"))

    # Scoped to the signed-in doctor: another doctor's id simply 404s.
    slot = DoctorAvailability.query.filter_by(id=slot_id, doctor_id=doctor.id).first_or_404()

    first_day, last_day = availability_service.window_bounds()
    form = AvailabilityEditForm(obj=slot)
    form.available_date.render_kw = {
        "min": first_day.isoformat(),
        "max": last_day.isoformat(),
    }

    if form.validate_on_submit():
        try:
            availability_service.update_slot(slot, form)
        except ValueError as error:
            flash(str(error), "warning")
        else:
            flash(f"Slot updated: {slot.available_date.strftime('%a, %d %b')} at {slot.label}.", "success")
            return redirect(url_for("doctor.availability"))

    return render_template(
        "doctor/availability_form.html",
        doctor=doctor,
        slot=slot,
        form=form,
        first_day=first_day,
        last_day=last_day,
    )


@doctor_bp.route("/availability/<int:slot_id>/delete", methods=["POST"])
@role_required(Role.DOCTOR)
def availability_delete(slot_id: int):
    """Remove an unused slot."""
    doctor = _current_doctor()
    if doctor is None:
        return redirect(url_for("main.index"))

    slot = DoctorAvailability.query.filter_by(id=slot_id, doctor_id=doctor.id).first_or_404()

    try:
        availability_service.delete_slot(slot)
    except ValueError as error:
        flash(str(error), "warning")
    else:
        flash("Slot removed.", "success")

    return redirect(url_for("doctor.availability"))


@doctor_bp.route("/availability/<int:slot_id>/toggle", methods=["POST"])
@role_required(Role.DOCTOR)
def availability_toggle(slot_id: int):
    """Hide a slot from patients, or show it again."""
    doctor = _current_doctor()
    if doctor is None:
        return redirect(url_for("main.index"))

    slot = DoctorAvailability.query.filter_by(id=slot_id, doctor_id=doctor.id).first_or_404()

    try:
        is_active = availability_service.toggle_slot(slot)
    except ValueError as error:
        flash(str(error), "warning")
    else:
        flash(
            f"Slot {slot.label} is now {'visible to patients' if is_active else 'hidden from patients'}.",
            "success" if is_active else "warning",
        )

    return redirect(url_for("doctor.availability"))
