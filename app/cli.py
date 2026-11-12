"""Custom Flask CLI commands.

Registered in create_app(). Usage:

    flask --app run.py init-db
"""

from __future__ import annotations

import click
from flask import Flask

from app.extensions import db
from app.models import Department, User
from app.utils.bootstrap import ensure_database


def register_cli(app: Flask) -> None:
    """Attach the project's CLI commands to the app."""

    @app.cli.command("init-db")
    def init_db_command() -> None:
        """Create missing tables and seed the admin account and departments."""
        ensure_database(app)

        with app.app_context():
            click.echo("Tables  : " + ", ".join(sorted(db.metadata.tables.keys())))
            click.echo(f"Users   : {User.query.count()}")
            click.echo(f"Departments: {Department.query.count()}")
            click.echo("Database initialised (idempotent - safe to run repeatedly).")
