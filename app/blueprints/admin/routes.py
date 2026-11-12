"""Administrator routes.

Task 5 provides the real dashboard; doctor, patient and department management
arrive in Tasks 6 and 7.
"""

from datetime import date

from flask import render_template

from app.blueprints.admin import admin_bp
from app.models import Role
from app.services.stats_service import admin_dashboard_stats, recent_appointments
from app.utils.decorators import role_required


@admin_bp.route("/dashboard")
@role_required(Role.ADMIN)
def dashboard():
    """Hospital-wide overview: doctors, patients, appointments, today's list."""
    return render_template(
        "admin/dashboard.html",
        stats=admin_dashboard_stats(),
        appointments=recent_appointments(),
        today=date.today(),
    )
