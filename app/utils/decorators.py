"""Route protection decorators.

Two layers of authorisation, applied together:

    @role_required(Role.ADMIN)      -> login + role + account-state check
    @role_required(Role.DOCTOR, Role.ADMIN)

Ownership checks ("is this *your* appointment?") happen inside the view,
because they need the record itself.
"""

from __future__ import annotations

from functools import wraps
from typing import Callable

from flask import abort, flash, redirect, request, url_for
from flask_login import current_user, logout_user

from app.extensions import login_manager
from app.models import User
from app.utils.security import is_safe_redirect


def role_required(*roles: str) -> Callable:
    """Allow the view only for logged-in users with one of the given roles.

    Behaviour:
      * anonymous        -> redirect to the login page (next=... preserved)
      * wrong role       -> 403 Forbidden
      * deactivated or
        blacklisted      -> session cleared, redirect to login with a message
    """

    def decorator(view: Callable) -> Callable:
        @wraps(view)
        def wrapped(*args, **kwargs):
            # NOTE: we check `is_anonymous` rather than using @login_required,
            # because Flask-Login's UserMixin.is_authenticated is just
            # `self.is_active`. A deactivated account would therefore look
            # "anonymous" and get the generic login prompt instead of a real
            # explanation - and its session would never be cleared.
            if current_user.is_anonymous:
                return login_manager.unauthorized()

            user: User = current_user

            # An account can be disabled while the user is still signed in,
            # so the state is re-checked on every protected request.
            if not user.can_log_in:
                logout_user()
                flash(
                    "Your account is no longer active. Please contact the hospital administration.",
                    "warning",
                )
                return redirect(url_for("auth.login"))

            if user.role not in roles:
                abort(403)

            return view(*args, **kwargs)

        return wrapped

    return decorator


def redirect_authenticated_user(view: Callable) -> Callable:
    """Send already signed-in users away from login/register pages."""
    from app.utils.security import dashboard_url

    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user.is_authenticated:
            return redirect(dashboard_url(current_user))
        return view(*args, **kwargs)

    return wrapped


def safe_next_url(fallback: str) -> str:
    """Return ?next= when it is a same-host URL, otherwise the fallback."""
    candidate = request.args.get("next")
    return candidate if is_safe_redirect(candidate) else fallback
