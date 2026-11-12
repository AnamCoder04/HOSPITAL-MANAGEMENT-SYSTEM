"""Administrator routes.

Doctor management (Task 7): list + search, create with a linked login account,
view, edit, activate/deactivate and a guarded delete. The other management
lists stay read-only until their own tasks.
"""

from __future__ import annotations

from datetime import date

from flask import flash, redirect, render_template, request, session, url_for
from sqlalchemy.exc import IntegrityError

from app.blueprints.admin import admin_bp
from app.blueprints.admin.forms import DoctorCreateForm, DoctorEditForm
from app.extensions import db
from app.models import Appointment, Department, Doctor, Patient, Role
from app.services import doctor_service
from app.services.stats_service import (
    admin_dashboard_stats,
    appointment_status_chart,
    doctor_dashboard_stats,
    recent_doctors,
    recent_patients,
)
from app.utils.decorators import role_required


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@admin_bp.route("/dashboard")
@role_required(Role.ADMIN)
def dashboard():
    """Hospital-wide overview: totals, status breakdown, recent activity."""
    stats = admin_dashboard_stats()

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        chart_data=appointment_status_chart(stats),
        recent_patients=recent_patients(),
        recent_doctors=recent_doctors(),
        today=date.today(),
    )


# ---------------------------------------------------------------------------
# Doctors
# ---------------------------------------------------------------------------
@admin_bp.route("/doctors")
@role_required(Role.ADMIN)
def doctors():
    """All doctors with optional name search and specialization filter."""
    search_name = (request.args.get("q") or "").strip()
    selected_specialization = (request.args.get("specialization") or "").strip()

    return render_template(
        "admin/doctors.html",
        doctors=doctor_service.search_doctors(search_name, selected_specialization),
        specializations=doctor_service.specializations(),
        search_name=search_name,
        selected_specialization=selected_specialization,
        total_doctors=Doctor.query.count(),
        busy_ids=doctor_service.busy_doctor_ids(),
    )


@admin_bp.route("/doctors/new", methods=["GET", "POST"])
@role_required(Role.ADMIN)
def doctor_create():
    """Create the doctor profile and its login account in one step."""
    form = DoctorCreateForm()

    if form.validate_on_submit():
        generated = form.password_mode.data == "generate"
        password = doctor_service.generate_password() if generated else form.password.data

        try:
            doctor = doctor_service.create_doctor(form, password)
        except IntegrityError:
            db.session.rollback()
            flash("That email address or licence number is already registered.", "danger")
        else:
            if generated:
                # Shown once on the profile page, never stored in plain text.
                session["doctor_credentials"] = {"doctor_id": doctor.id, "password": password}
            flash(f"Dr. {doctor.full_name} was added and can now sign in.", "success")
            return redirect(url_for("admin.doctor_view", doctor_id=doctor.id))

    return render_template(
        "admin/doctor_form.html",
        form=form,
        mode="create",
        specializations=doctor_service.specializations(),
    )


@admin_bp.route("/doctors/<int:doctor_id>")
@role_required(Role.ADMIN)
def doctor_view(doctor_id: int):
    """Full profile of one doctor, with their activity and history rules."""
    doctor = db.get_or_404(Doctor, doctor_id)

    # Show a generated password exactly once, on this doctor's page.
    credentials = session.pop("doctor_credentials", None)
    if credentials and credentials.get("doctor_id") != doctor.id:
        session["doctor_credentials"] = credentials
        credentials = None

    today = date.today()
    upcoming_slots = [
        slot for slot in doctor.availabilities
        if slot.is_active and slot.available_date >= today
    ][:7]

    return render_template(
        "admin/doctor_view.html",
        doctor=doctor,
        stats=doctor_dashboard_stats(doctor),
        history=doctor_service.doctor_history(doctor),
        can_delete=doctor_service.can_delete_doctor(doctor),
        credentials=credentials,
        upcoming_slots=upcoming_slots,
        recent_appointments=doctor.appointments[:5],
        today=today,
    )


@admin_bp.route("/doctors/<int:doctor_id>/edit", methods=["GET", "POST"])
@role_required(Role.ADMIN)
def doctor_edit(doctor_id: int):
    """Update the account details and the professional profile."""
    doctor = db.get_or_404(Doctor, doctor_id)
    form = DoctorEditForm(doctor=doctor)

    if form.validate_on_submit():
        try:
            doctor_service.update_doctor(doctor, form)
        except IntegrityError:
            db.session.rollback()
            flash("That email address or licence number is already registered.", "danger")
        else:
            flash(f"Dr. {doctor.full_name}'s details were updated.", "success")
            return redirect(url_for("admin.doctor_view", doctor_id=doctor.id))

    elif request.method == "GET":
        form.full_name.data = doctor.full_name
        form.email.data = doctor.email
        form.phone.data = doctor.phone
        form.department_id.data = doctor.department_id
        form.specialization.data = doctor.specialization
        form.qualifications.data = doctor.qualifications
        form.license_no.data = doctor.license_no
        form.experience_years.data = doctor.experience_years
        form.consultation_fee.data = doctor.consultation_fee
        form.room_no.data = doctor.room_no
        form.bio.data = doctor.bio
        form.is_available.data = doctor.is_available

    return render_template(
        "admin/doctor_form.html",
        form=form,
        mode="edit",
        doctor=doctor,
        specializations=doctor_service.specializations(),
    )


@admin_bp.route("/doctors/<int:doctor_id>/toggle", methods=["POST"])
@role_required(Role.ADMIN)
def doctor_toggle(doctor_id: int):
    """Activate or deactivate the doctor's login account."""
    doctor = db.get_or_404(Doctor, doctor_id)
    is_active = doctor_service.toggle_doctor_active(doctor)

    if is_active:
        flash(f"Dr. {doctor.full_name}'s account was activated.", "success")
    else:
        flash(
            f"Dr. {doctor.full_name}'s account was deactivated. "
            "Their records and appointments are unchanged.",
            "warning",
        )
    return redirect(url_for("admin.doctor_view", doctor_id=doctor.id))


@admin_bp.route("/doctors/<int:doctor_id>/delete", methods=["POST"])
@role_required(Role.ADMIN)
def doctor_delete(doctor_id: int):
    """Delete a doctor only when they have no appointment or treatment history."""
    doctor = db.get_or_404(Doctor, doctor_id)
    name = doctor.full_name

    try:
        doctor_service.delete_doctor(doctor)
    except ValueError as error:
        flash(str(error), "warning")
        return redirect(url_for("admin.doctor_view", doctor_id=doctor_id))

    flash(f"Dr. {name} was deleted.", "success")
    return redirect(url_for("admin.doctors"))


# ---------------------------------------------------------------------------
# Patients / appointments / departments (read-only for now)
# ---------------------------------------------------------------------------
@admin_bp.route("/patients")
@role_required(Role.ADMIN)
def patients():
    """Every patient account, newest first."""
    patients_list = Patient.query.order_by(Patient.created_at.desc()).all()
    return render_template("admin/patients.html", patients=patients_list)


@admin_bp.route("/appointments")
@role_required(Role.ADMIN)
def appointments():
    """All appointments across every doctor and patient."""
    appointments_list = Appointment.query.order_by(
        Appointment.appointment_date.desc(),
        Appointment.appointment_time.desc(),
    ).all()
    return render_template("admin/appointments.html", appointments=appointments_list)


@admin_bp.route("/departments")
@role_required(Role.ADMIN)
def departments():
    """Departments with their doctor counts."""
    departments_list = Department.query.order_by(Department.name).all()
    return render_template("admin/departments.html", departments=departments_list)
