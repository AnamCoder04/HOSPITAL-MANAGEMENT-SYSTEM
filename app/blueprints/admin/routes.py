"""Administrator routes.

Doctor management (Task 7): list + search, create with a linked login account,
view, edit, activate/deactivate and a guarded delete.
Patient management (Task 8): paginated list with name / patient-ID / phone
search, profile with appointment and treatment history, editing and account
deactivation. Patients are never deleted, because their appointments and
treatment records are medical history.

The remaining management lists stay read-only until their own tasks.
"""

from __future__ import annotations

from datetime import date

from flask import current_app, flash, redirect, render_template, request, session, url_for
from sqlalchemy.exc import IntegrityError

from app.blueprints.admin import admin_bp
from app.blueprints.admin.forms import (
    DepartmentForm,
    DepartmentSearchForm,
    DoctorCreateForm,
    DoctorEditForm,
    PatientEditForm,
    PatientSearchForm,
)
from app.extensions import db
from app.models import Appointment, Department, Doctor, Patient, Role
from app.services import department_service, doctor_service, patient_service
from app.services.stats_service import (
    admin_dashboard_stats,
    appointment_status_chart,
    doctor_dashboard_stats,
    patient_dashboard_stats,
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
# Patients
# ---------------------------------------------------------------------------
@admin_bp.route("/patients")
@role_required(Role.ADMIN)
def patients():
    """Paginated patient list, searchable by name, patient ID and phone."""
    form = PatientSearchForm(request.args)
    form.validate()  # a GET filter form: invalid input is shown, not applied blindly

    page = request.args.get("page", 1, type=int) or 1
    pager = patient_service.search_patients(
        name=form.q.data or "",
        patient_code=form.patient_id.data or "",
        phone=form.phone.data or "",
        page=page,
        per_page=current_app.config["ITEMS_PER_PAGE"],
    )

    # Only non-empty filters are carried into pagination links.
    filters = {
        key: value
        for key, value in {
            "q": form.q.data,
            "patient_id": form.patient_id.data,
            "phone": form.phone.data,
        }.items()
        if value
    }

    return render_template(
        "admin/patients.html",
        form=form,
        pager=pager,
        patients=pager.items,
        filters=filters,
        total_patients=Patient.query.count(),
    )


@admin_bp.route("/patients/<int:patient_id>")
@role_required(Role.ADMIN)
def patient_view(patient_id: int):
    """One patient's profile, appointment history and treatment history."""
    patient = db.get_or_404(Patient, patient_id)
    page = request.args.get("page", 1, type=int) or 1

    pager = patient_service.appointments_page(
        patient, page=page, per_page=current_app.config["ITEMS_PER_PAGE"]
    )
    treatments = patient_service.patient_treatments(patient)

    return render_template(
        "admin/patient_view.html",
        patient=patient,
        stats=patient_dashboard_stats(patient),
        pager=pager,
        appointments=pager.items,
        treatments=treatments,
        history=patient_service.medical_history_summary(patient),
    )


@admin_bp.route("/patients/<int:patient_id>/edit", methods=["GET", "POST"])
@role_required(Role.ADMIN)
def patient_edit(patient_id: int):
    """Correct a patient's contact details and medical profile."""
    patient = db.get_or_404(Patient, patient_id)
    form = PatientEditForm(patient=patient)

    if form.validate_on_submit():
        try:
            patient_service.update_patient(patient, form)
        except IntegrityError:
            db.session.rollback()
            flash("That email address is already used by another account.", "danger")
        else:
            flash(f"{patient.full_name}'s details were updated.", "success")
            return redirect(url_for("admin.patient_view", patient_id=patient.id))

    elif request.method == "GET":
        form.full_name.data = patient.full_name
        form.email.data = patient.email
        form.phone.data = patient.phone
        form.date_of_birth.data = patient.date_of_birth
        form.gender.data = patient.gender or ""
        form.blood_group.data = patient.blood_group or ""
        form.address.data = patient.address
        form.emergency_contact.data = patient.emergency_contact
        form.allergies.data = patient.allergies

    return render_template(
        "admin/patient_form.html",
        form=form,
        patient=patient,
        history=patient_service.medical_history_summary(patient),
    )


@admin_bp.route("/patients/<int:patient_id>/toggle", methods=["POST"])
@role_required(Role.ADMIN)
def patient_toggle(patient_id: int):
    """Deactivate or reactivate a patient's login. History is untouched."""
    patient = db.get_or_404(Patient, patient_id)
    is_active = patient_service.toggle_patient_active(patient)

    if is_active:
        flash(f"{patient.full_name}'s account was reactivated.", "success")
    else:
        flash(
            f"{patient.full_name}'s account was deactivated. "
            "Appointments and treatment records are unchanged.",
            "warning",
        )
    return redirect(url_for("admin.patient_view", patient_id=patient.id))


# ---------------------------------------------------------------------------
# Appointments / departments (read-only for now)
# ---------------------------------------------------------------------------


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
    """All departments, searchable by name/description and filterable by state."""
    form = DepartmentSearchForm(request.args)
    form.validate()  # GET filter form: errors are shown inline

    term = form.q.data or ""
    status = form.status.data or "all"

    return render_template(
        "admin/departments.html",
        form=form,
        departments=department_service.search_departments(term, status),
        total_departments=Department.query.count(),
        active_departments=Department.query.filter_by(is_active=True).count(),
        filters={key: value for key, value in {"q": term, "status": status if status != "all" else ""}.items() if value},
    )


@admin_bp.route("/departments/new", methods=["GET", "POST"])
@role_required(Role.ADMIN)
def department_create():
    """Create a department."""
    form = DepartmentForm()

    if form.validate_on_submit():
        try:
            department = department_service.create_department(form)
        except IntegrityError:
            db.session.rollback()
            flash("A department with this name already exists.", "danger")
        else:
            flash(f"{department.name} was added.", "success")
            return redirect(url_for("admin.department_view", department_id=department.id))

    return render_template("admin/department_form.html", form=form, mode="create")


@admin_bp.route("/departments/<int:department_id>")
@role_required(Role.ADMIN)
def department_view(department_id: int):
    """Department details and every doctor registered under it."""
    department = db.get_or_404(Department, department_id)

    return render_template(
        "admin/department_view.html",
        department=department,
        stats=department_service.department_stats(department),
        doctors=department_service.department_doctors(department),
        can_deactivate=department_service.can_deactivate(department),
    )


@admin_bp.route("/departments/<int:department_id>/edit", methods=["GET", "POST"])
@role_required(Role.ADMIN)
def department_edit(department_id: int):
    """Rename a department, change its description or retire it."""
    department = db.get_or_404(Department, department_id)
    form = DepartmentForm(department=department)

    if form.validate_on_submit():
        try:
            department_service.update_department(department, form)
        except IntegrityError:
            db.session.rollback()
            flash("A department with this name already exists.", "danger")
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "warning")
        else:
            flash(f"{department.name} was updated.", "success")
            return redirect(url_for("admin.department_view", department_id=department.id))

    elif request.method == "GET":
        form.name.data = department.name
        form.description.data = department.description
        form.is_active.data = department.is_active

    return render_template(
        "admin/department_form.html",
        form=form,
        mode="edit",
        department=department,
    )


@admin_bp.route("/departments/<int:department_id>/toggle", methods=["POST"])
@role_required(Role.ADMIN)
def department_toggle(department_id: int):
    """Retire or reactivate a department. Doctors and history are untouched."""
    department = db.get_or_404(Department, department_id)

    try:
        is_active = department_service.toggle_department_active(department)
    except ValueError as error:
        flash(str(error), "warning")
        return redirect(url_for("admin.department_view", department_id=department.id))

    if is_active:
        flash(f"{department.name} is active again and accepts doctor assignments.", "success")
    else:
        flash(
            f"{department.name} was retired. Doctors and appointment history are unchanged.",
            "warning",
        )
    return redirect(url_for("admin.department_view", department_id=department.id))
