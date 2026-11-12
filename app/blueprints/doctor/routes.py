"""Doctor routes.

Task 5 provides the real dashboard; appointments, availability and medical
records arrive in Tasks 8 and 10.
"""

from __future__ import annotations

from datetime import date

from flask import flash, redirect, render_template, url_for
from flask_login import current_user

from app.blueprints.doctor import doctor_bp
from app.models import Role
from app.services.stats_service import doctor_dashboard_stats, todays_appointments_for_doctor
from app.utils.decorators import role_required


@doctor_bp.route("/dashboard")
@role_required(Role.DOCTOR)
def dashboard():
    """This doctor's own overview: today's schedule and counts."""
    doctor = current_user.doctor

    # Defensive: a doctor account without a profile cannot show anything.
    if doctor is None:
        flash("Your doctor profile is not set up yet. Please contact the administrator.", "warning")
        return redirect(url_for("main.index"))

    return render_template(
        "doctor/dashboard.html",
        doctor=doctor,
        stats=doctor_dashboard_stats(doctor),
        todays_appointments=todays_appointments_for_doctor(doctor),
        today=date.today(),
    )
