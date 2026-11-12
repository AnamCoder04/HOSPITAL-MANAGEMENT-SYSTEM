"""Public blueprint: landing page and (from Task 6) the doctor directory."""

from flask import Blueprint

main_bp = Blueprint("main", __name__)

# Imported at the bottom so the blueprint exists before routes are attached
# (this is the standard way to avoid circular imports with blueprints).
from app.blueprints.main import routes  # noqa: E402,F401
