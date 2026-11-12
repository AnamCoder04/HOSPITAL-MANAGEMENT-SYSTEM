"""Flask extension instances.

The extensions are created here, without an application, and bound to the
app inside create_app() via init_app(). This is what keeps the app factory
free of circular imports: models import `db` from here, and the factory
imports the models.
"""

from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import event
from sqlalchemy.engine import Engine

# ORM: models -> tables in SQLite
db = SQLAlchemy()

# Session-based authentication
login_manager = LoginManager()

# CSRF token protection for every POSTed form
csrf = CSRFProtect()


# --- SQLite: enforce foreign keys --------------------------------------------
# SQLite ignores FOREIGN KEY constraints unless this pragma is switched on for
# every connection. Without it, deleting a user would leave orphaned doctor /
# patient / appointment rows behind.
@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record) -> None:
    if dbapi_connection.__class__.__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# --- Flask-Login defaults ---------------------------------------------------
# Where anonymous users are sent by @login_required.
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to continue."
login_manager.login_message_category = "warning"
# Session token that remembers the browser ("remember me" support).
login_manager.session_protection = "strong"


# --- Flask-Login user loader ------------------------------------------------
# The @login_manager.user_loader callback lives next to the User model, in
# app/models/user.py, because it needs to query the users table. Flask-Login
# also registers a context processor that resolves `current_user` on every
# template render, so that callback must exist for any page to render.
