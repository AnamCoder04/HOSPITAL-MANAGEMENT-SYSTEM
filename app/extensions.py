"""Flask extension instances.

The extensions are created here, without an application, and bound to the
app inside create_app() via init_app(). This is what keeps the app factory
free of circular imports: models import `db` from here, and the factory
imports the models.
"""

from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

# ORM: models -> tables in SQLite
db = SQLAlchemy()

# Session-based authentication
login_manager = LoginManager()

# CSRF token protection for every POSTed form
csrf = CSRFProtect()


# --- Flask-Login defaults ---------------------------------------------------
# Where anonymous users are sent by @login_required.
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to continue."
login_manager.login_message_category = "warning"
# Session token that remembers the browser ("remember me" support).
login_manager.session_protection = "strong"


# --- Flask-Login user loader ------------------------------------------------
# Flask-Login registers a context processor that resolves `current_user` on
# EVERY template render, so a user_loader must exist even before anyone can
# log in. Task 3 replaces the body below with the real database lookup:
#
#     from app.models import User
#     return db.session.get(User, int(user_id))
#
# Returning None simply means "no user is logged in", which is exactly the
# state we want until authentication is implemented in Task 4.
@login_manager.user_loader
def load_user(user_id: str):
    return None
