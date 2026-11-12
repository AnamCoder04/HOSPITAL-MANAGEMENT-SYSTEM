"""WTForms for authentication.

Every field is validated on the server with Flask-WTF; the HTML5 attributes
in the templates are only a convenience for the user.
"""

from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length,
    Regexp,
    ValidationError,
)

from app.models import User

# At least one letter and one digit, 8 characters or more (length is enforced
# by a separate validator so the messages stay specific).
PASSWORD_PATTERN = r"^(?=.*[A-Za-z])(?=.*\d).+$"
PHONE_PATTERN = r"^\+?[0-9][0-9\s\-]{8,14}$"


def strip_whitespace(value):
    """Field filter: remove leading/trailing spaces BEFORE validation.

    People paste addresses with stray spaces; without this the email validator
    would reject " name@example.com " even though it is perfectly valid.
    """
    return value.strip() if isinstance(value, str) else value


class LoginForm(FlaskForm):
    """One form for all three roles - the role is read from the database."""

    # No Email() validator here on purpose: the address only has to exist in
    # the database, and strict format validators reject reserved domains such
    # as admin@hospital.local that a real deployment may legitimately use.
    # Registration still validates the format strictly.
    email = StringField(
        "Email address",
        filters=[strip_whitespace],
        validators=[
            DataRequired(message="Please enter your email."),
            Length(max=150, message="Email address is too long."),
        ],
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(message="Please enter your password."),
            Length(min=6, max=128),
        ],
    )
    remember = BooleanField("Keep me signed in")
    submit = SubmitField("Sign in")


class PatientRegisterForm(FlaskForm):
    """Self-registration. Creates a Patient account only - never an admin."""

    full_name = StringField(
        "Full name",
        filters=[strip_whitespace],
        validators=[
            DataRequired(message="Please enter your full name."),
            Length(min=3, max=120, message="Name must be between 3 and 120 characters."),
        ],
    )
    email = StringField(
        "Email address",
        filters=[strip_whitespace],
        validators=[
            DataRequired(message="Please enter your email."),
            Email(message="Enter a valid email address, e.g. name@example.com."),
            Length(max=150),
        ],
    )
    phone = StringField(
        "Contact number",
        filters=[strip_whitespace],
        validators=[
            DataRequired(message="Please enter a contact number."),
            Regexp(PHONE_PATTERN, message="Enter a valid phone number (10-15 digits)."),
        ],
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(message="Choose a password."),
            Length(min=8, max=128, message="Password must be at least 8 characters."),
            Regexp(PASSWORD_PATTERN, message="Password must contain at least one letter and one number."),
        ],
    )
    confirm_password = PasswordField(
        "Confirm password",
        validators=[
            DataRequired(message="Repeat your password."),
            EqualTo("password", message="Passwords do not match."),
        ],
    )
    submit = SubmitField("Create patient account")

    def validate_email(self, field: StringField) -> None:
        """Reject an e-mail that already has an account (case-insensitive)."""
        if User.query.filter_by(email=field.data.strip().lower()).first():
            raise ValidationError("An account with this email already exists. Please sign in instead.")

    def validate_full_name(self, field: StringField) -> None:
        """Collapse repeated spaces so 'A  B' and 'A B' are treated the same."""
        cleaned = " ".join(field.data.split())
        if len(cleaned) < 3:
            raise ValidationError("Please enter your full name.")
        field.data = cleaned
