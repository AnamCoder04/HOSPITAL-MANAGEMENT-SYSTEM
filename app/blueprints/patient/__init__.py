"""Patient blueprint (URL prefix /patient)."""

from flask import Blueprint

patient_bp = Blueprint("patient", __name__, url_prefix="/patient")

from app.blueprints.patient import routes  # noqa: E402,F401
