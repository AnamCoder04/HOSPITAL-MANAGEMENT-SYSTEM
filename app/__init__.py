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

    # 4. Template globals / context processors ----------------------------
    register_template_context(app)

    return app


def register_blueprints(app: Flask) -> None:
    """Attach every blueprint to the application."""
    from app.blueprints.main import main_bp

    app.register_blueprint(main_bp)

    # Task 4+ : app.register_blueprint(auth_bp)
    # Task 6+ : app.register_blueprint(admin_bp)
    # Task 8+ : app.register_blueprint(doctor_bp)
    # Task 9+ : app.register_blueprint(patient_bp)


def register_template_context(app: Flask) -> None:
    """Values available in every Jinja2 template."""

    @app.context_processor
    def inject_globals() -> dict:
        return {
            "hospital_name": app.config["HOSPITAL_NAME"],
            "hospital_tagline": app.config["HOSPITAL_TAGLINE"],
            "current_year": datetime.now().year,
        }
