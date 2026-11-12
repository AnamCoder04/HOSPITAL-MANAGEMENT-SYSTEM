"""MediCare HMS application factory.

Everything the application needs is assembled here:

    create_app()
        -> load configuration          (config.py)
        -> bind extensions             (app/extensions.py)
        -> register blueprints         (app/blueprints/*)
        -> register template helpers   (hospital name, current year)
"""

import os
from datetime import datetime

from flask import Flask

from app.extensions import csrf, db, login_manager
from app.utils.security import dashboard_url
from config import get_config


def create_app(config_name: str | None = None) -> Flask:
    """Build and configure a Flask application instance."""
    app = Flask(__name__, instance_relative_config=True)

    # 1. Configuration ----------------------------------------------------
    app.config.from_object(get_config(config_name))

    # Flask puts per-installation data (the SQLite file) in instance/.
    os.makedirs(app.instance_path, exist_ok=True)

    # 2. Extensions -------------------------------------------------------
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # 3. Blueprints -------------------------------------------------------
    register_blueprints(app)

    # 4. CLI commands -----------------------------------------------------
    from app.cli import register_cli

    register_cli(app)

    # 5. Error pages ------------------------------------------------------
    register_error_handlers(app)

    # 5. Database ---------------------------------------------------------
    # Creates any missing tables, the default admin and the starter
    # departments. Idempotent, so it is safe on every start.
    from app.utils.bootstrap import ensure_database

    ensure_database(app)

    # 6. Template globals / context processors ----------------------------
    register_template_context(app)

    return app


def register_blueprints(app: Flask) -> None:
    """Attach every blueprint to the application."""
    from app.blueprints.admin import admin_bp
    from app.blueprints.auth import auth_bp
    from app.blueprints.doctor import doctor_bp
    from app.blueprints.main import main_bp
    from app.blueprints.patient import patient_bp

    app.register_blueprint(main_bp)      # /            public pages
    app.register_blueprint(auth_bp)      # /auth/*      login, register, logout
    app.register_blueprint(admin_bp)     # /admin/*     administrator portal
    app.register_blueprint(doctor_bp)    # /doctor/*    doctor portal
    app.register_blueprint(patient_bp)   # /patient/*   patient portal


def register_template_context(app: Flask) -> None:
    """Values available in every Jinja2 template."""

    @app.context_processor
    def inject_globals() -> dict:
        return {
            "hospital_name": app.config["HOSPITAL_NAME"],
            "hospital_tagline": app.config["HOSPITAL_TAGLINE"],
            "current_year": datetime.now().year,
            "dashboard_url": dashboard_url,
        }


def register_error_handlers(app: Flask) -> None:
    """Friendly pages instead of raw HTTP errors."""
    from flask import render_template
    from werkzeug.exceptions import Forbidden

    @app.errorhandler(403)
    def forbidden(error: Forbidden):
        return render_template("errors/403.html"), 403
