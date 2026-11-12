"""Administrator routes.

Task 4 provides the protected dashboard that login redirects to; doctor,
patient and department management arrive in Tasks 6 and 7.
"""

from __future__ import annotations

from flask import render_template

from app.blueprints.admin import admin_bp
from app.models import Role
from app.utils.decorators import role_required


@admin_bp.route("/dashboard")
@role_required(Role.ADMIN)
def dashboard():
    """Admin landing page after login."""
    return render_template("admin/dashboard.html")
