"""Administrator blueprint (URL prefix /admin)."""

from flask import Blueprint

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.after_request
def _no_store(response):
    """Administrator pages contain patient information, so never cache them.

    Stops a shared computer's browser from keeping a copy of a patient list,
    profile or treatment record after the admin signs out.
    """
    response.headers["Cache-Control"] = "no-store"
    return response


from app.blueprints.admin import routes  # noqa: E402,F401
