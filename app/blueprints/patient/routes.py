"""Patient routes.

Task 5 provides the real dashboard; doctor search, booking and records arrive
in Tasks 9 and 10.
"""

from __future__ import annotations

from datetime import date

from flask import flash, redirect, render_template, url_for
from flask_login import current_user

from app.blueprints.patient import patient_bp
from app.models import Role
from app.services.stats_service import patient_dashboard_stats, upcoming_appointments_for_patient
from app.utils.decorators import role_required


@patient_bp.route("/dashboard")
@role_required(Role.PATIENT)
def dashboard():
    """This patient's own overview: next visit, counts and upcoming list."""
    patient = current_user.patient

    if patient is None:
        flash("Your patient profile is not set up yet. Please contact the hospital.", "warning")
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
