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

from flask import Flask, current_app

from app.extensions import csrf, db, login_manager
from app.utils.security import dashboard_url
from config import get_config


def create_app(config_name: str | None = None) -> Flask:
    """Build and configure a Flask application instance."""
    app = Flask(__name__, instance_relative_config=True)

    # 1. Configuration ----------------------------------------------------
    app.config.from_object(get_config(config_name))

    # Flask puts per-installation data (the SQLite file) in instance/.
    # On a read-only host such as Vercel that directory cannot be created, so
    # the failure is tolerated: the configured database path lives elsewhere
    # (/tmp) and its directory is created just below.
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        app.logger.debug("instance/ is not writable; using the configured database path")

    _ensure_database_directory(app)

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

    # Optional demo data (automatic on Vercel, see config.AUTO_SEED_DEMO).
    # The seeder is idempotent, so this is safe on every cold start.
    if app.config.get("AUTO_SEED_DEMO"):
        try:
            from seed_demo import seed as seed_demo_data

            seed_demo_data(app, quiet=True)
        except Exception:  # pragma: no cover - never block boot on demo data
            app.logger.exception("Demo data could not be seeded")

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
        # Endpoints registered so far. The sidebar templates use this to render
        # a muted "soon" item for pages that arrive in a later task instead of
        # raising a BuildError from url_for().
        available_endpoints = {rule.endpoint for rule in current_app.url_map.iter_rules()}

        return {
            "hospital_name": app.config["HOSPITAL_NAME"],
            "hospital_tagline": app.config["HOSPITAL_TAGLINE"],
            "current_year": datetime.now().year,
            "dashboard_url": dashboard_url,
            "available_endpoints": available_endpoints,
        }


def _ensure_database_directory(app: Flask) -> None:
    """Create the parent directory of an absolute SQLite database path.

    Flask-SQLAlchemy resolves relative paths inside instance/, but a path such
    as /tmp/medicare/hms.sqlite3 (used on Vercel) has to exist before SQLite
    can open the file. Non-SQLite URLs are left alone.
    """
    from sqlalchemy.engine import make_url

    uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if not uri.startswith("sqlite"):
        return

    database = make_url(uri).database
    if database and database != ":memory:" and os.path.isabs(database):
        os.makedirs(os.path.dirname(database), exist_ok=True)


def register_error_handlers(app: Flask) -> None:
    """Friendly pages instead of raw HTTP errors."""
    from flask import render_template
    from werkzeug.exceptions import Forbidden

    @app.errorhandler(403)
    def forbidden(error: Forbidden):
        return render_template("errors/403.html"), 403
