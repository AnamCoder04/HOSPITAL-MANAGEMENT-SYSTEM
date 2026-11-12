"""Programmatic database initialisation.

Called once from create_app(), so starting the application is all it takes to
get a working database:

    ensure_database(app)
        1. db.create_all()          -> creates any missing tables
        2. ensure_admin()           -> creates the default admin if missing
        3. ensure_departments()     -> seeds the starter departments

Every step is idempotent: restarting the app never duplicates a row and never
resets a password.
"""

from __future__ import annotations

from flask import Flask

from app.extensions import db
from app.models import Department, Role, User

# Starter departments (name, description). Adding one here only affects a
# database that does not already contain that department name.
DEFAULT_DEPARTMENTS = [
    ("General Medicine", "First point of contact for general illness and check-ups."),
    ("Cardiology", "Heart, blood vessels and circulatory care."),
    ("Orthopaedics", "Bones, joints, muscles and sports injuries."),
    ("Paediatrics", "Medical care for infants, children and adolescents."),
    ("Dermatology", "Skin, hair and nail conditions."),
    ("Neurology", "Brain, spinal cord and nervous system disorders."),
    ("ENT", "Ear, nose and throat conditions."),
    ("Gynaecology", "Women's reproductive health."),
]


def ensure_database(app: Flask) -> None:
    """Create tables and seed the minimum data the app needs to run."""
    with app.app_context():
        db.create_all()
        ensure_schema_upgrades(app)

        admin = ensure_admin(app)
        created_departments = ensure_departments()

        app.logger.info(
            "Database ready: admin=%s, departments created=%s",
            admin.email if admin else "missing",
            created_departments,
        )


def ensure_schema_upgrades(app: Flask) -> None:
    """Add columns introduced after a database was first created.

    `db.create_all()` only creates *missing tables*; it never alters an
    existing one. SQLite supports `ALTER TABLE ... ADD COLUMN`, so a small
    additive upgrade keeps an existing database usable without a migration
    tool. Destructive changes would need Flask-Migrate.
    """
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    if "doctors" not in inspector.get_table_names():
        return  # brand-new database: create_all already built the full schema

    doctor_columns = {column["name"] for column in inspector.get_columns("doctors")}
    if "qualifications" not in doctor_columns:
        db.session.execute(text("ALTER TABLE doctors ADD COLUMN qualifications VARCHAR(200)"))
        db.session.commit()
        app.logger.info("Schema upgrade: added doctors.qualifications")


def ensure_admin(app: Flask) -> User | None:
    """Create the default administrator if no account with that email exists.

    The credentials come from the environment (ADMIN_EMAIL / ADMIN_PASSWORD),
    so no password is ever hard-coded in the source.
    """
    email = (app.config.get("ADMIN_EMAIL") or "").strip().lower()
    password = app.config.get("ADMIN_PASSWORD") or ""
    name = app.config.get("ADMIN_NAME") or "System Administrator"

    if not email or not password:
        app.logger.warning("ADMIN_EMAIL / ADMIN_PASSWORD not configured; skipping admin bootstrap.")
        return None

    existing = User.query.filter_by(email=email).first()
    if existing:
        if existing.role != Role.ADMIN:
            app.logger.warning(
                "Seed admin email %s already belongs to a '%s' account; leaving it untouched.",
                email,
                existing.role,
            )
        return existing

    admin = User(
        full_name=name,
        email=email,
        role=Role.ADMIN,
        is_active=True,
        is_blacklisted=False,
    )
    admin.set_password(password)  # stored as a Werkzeug hash, never plain text

    db.session.add(admin)
    db.session.commit()

    app.logger.info("Created default admin account: %s", admin.email)
    return admin


def ensure_departments() -> int:
    """Insert any starter department that does not exist yet. Returns a count."""
    created = 0
    for name, description in DEFAULT_DEPARTMENTS:
        if not Department.query.filter_by(name=name).first():
            db.session.add(Department(name=name, description=description))
            created += 1

    if created:
        db.session.commit()
    return created
