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
from app.blueprints.doctor.forms import AvailabilityEditForm, AvailabilityForm
from app.extensions import db
from app.models import DoctorAvailability, Role
from app.services import availability_service
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
