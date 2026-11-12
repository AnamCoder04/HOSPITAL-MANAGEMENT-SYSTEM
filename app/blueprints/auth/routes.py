"""Authentication routes: login, patient registration, logout."""

from __future__ import annotations

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError

from app.blueprints.auth import auth_bp
from app.blueprints.auth.forms import LoginForm, PatientRegisterForm
from app.extensions import db
from app.models import Patient, Role, User, utcnow
from app.utils.decorators import redirect_authenticated_user, safe_next_url
from app.utils.security import dashboard_url


@auth_bp.route("/login", methods=["GET", "POST"])
@redirect_authenticated_user
def login():
    """Sign in an admin, doctor or patient with one form."""
    form = LoginForm()

    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter_by(email=email).first()

        # Same message for "unknown email" and "wrong password" so the form
        # cannot be used to discover which addresses have accounts.
        if user is None or not user.check_password(form.password.data):
            flash("Invalid email or password. Please try again.", "danger")

        elif not user.is_active:
            flash(
                "This account has been deactivated by the hospital administration. "
                "Please contact the front desk.",
                "danger",
            )

        elif user.is_blacklisted:
            reason = f" Reason given: {user.blacklist_reason}." if user.blacklist_reason else ""
            flash(f"This account has been blacklisted and cannot sign in.{reason}", "danger")

        else:
            login_user(user, remember=form.remember.data)
            user.last_login = utcnow()
            db.session.commit()

            flash(f"Welcome back, {user.full_name}.", "success")
            return redirect(safe_next_url(dashboard_url(user)))

    elif request.method == "POST":
        flash("Please correct the highlighted fields and try again.", "warning")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/register", methods=["GET", "POST"])
@redirect_authenticated_user
def register():
    """Patient self-registration.

    There is deliberately no admin or doctor registration: admins are seeded
    at start-up and doctor accounts are created by an administrator.
    """
    form = PatientRegisterForm()

    if form.validate_on_submit():
        user = User(
            full_name=form.full_name.data,
            email=form.email.data.strip().lower(),
            phone=form.phone.data.strip(),
            role=Role.PATIENT,
        )
        user.set_password(form.password.data)

        try:
            db.session.add(user)
            db.session.flush()  # assigns user.id so the patient code can be built

            # patient_code (PAT-000001) is generated automatically on insert.
            db.session.add(Patient(user_id=user.id))
            db.session.commit()
        except IntegrityError:
            # Belt and braces: the UNIQUE index on users.email is the final
            # guard if two registrations race past the form-level check.
            db.session.rollback()
            flash("That email address was just registered. Please sign in instead.", "danger")
        else:
            login_user(user)
            flash(
                "Your patient account is ready. You can book an appointment right away.",
                "success",
            )
            return redirect(url_for("patient.dashboard"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """Sign out. POST-only so a stray link or image cannot log the user out."""
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))
