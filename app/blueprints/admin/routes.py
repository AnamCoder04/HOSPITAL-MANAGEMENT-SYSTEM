"""Administrator routes.

Task 6: the data-driven dashboard plus the read-only management lists that
its shortcuts point to. Create/edit forms and search arrive next.
"""

from __future__ import annotations

from datetime import date

from flask import render_template

from app.blueprints.admin import admin_bp
from app.models import Appointment, Department, Doctor, Patient, Role
from app.services.stats_service import (
    admin_dashboard_stats,
    appointment_status_chart,
    recent_doctors,
    recent_patients,
)
from app.utils.decorators import role_required


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


@admin_bp.route("/doctors")
@role_required(Role.ADMIN)
def doctors():
    """Every doctor profile, newest first."""
    doctors_list = (
        Doctor.query.join(Doctor.user)
        .order_by(Doctor.created_at.desc())
        .all()
    )
    return render_template("admin/doctors.html", doctors=doctors_list)


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
