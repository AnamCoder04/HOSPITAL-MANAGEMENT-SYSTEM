"""Doctor routes.

Task 4 provides the protected dashboard; appointments, availability and
medical records arrive in Tasks 8 and 10.
"""

from __future__ import annotations

from flask import render_template

from app.blueprints.doctor import doctor_bp
from app.models import Role
from app.utils.decorators import role_required


@doctor_bp.route("/dashboard")
@role_required(Role.DOCTOR)
def dashboard():
    """Doctor landing page after login."""
    return render_template("doctor/dashboard.html")
