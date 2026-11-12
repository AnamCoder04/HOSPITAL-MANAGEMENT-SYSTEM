"""Doctor blueprint (URL prefix /doctor)."""

from flask import Blueprint

doctor_bp = Blueprint("doctor", __name__, url_prefix="/doctor")

from app.blueprints.doctor import routes  # noqa: E402,F401
