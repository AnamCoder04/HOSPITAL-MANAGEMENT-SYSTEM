"""Patient routes.

Task 4 provides the protected dashboard; booking, history and profile
management arrive in Tasks 9 and 10.
"""

from __future__ import annotations

from flask import render_template

from app.blueprints.patient import patient_bp
from app.models import Role
from app.utils.decorators import role_required


@patient_bp.route("/dashboard")
@role_required(Role.PATIENT)
def dashboard():
    """Patient landing page after login."""
    return render_template("patient/dashboard.html")
