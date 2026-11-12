"""Public routes."""

from flask import render_template

from app.blueprints.main import main_bp


@main_bp.route("/")
def index():
    """Landing page: what the hospital offers and how to get started."""
    return render_template("main/index.html")
