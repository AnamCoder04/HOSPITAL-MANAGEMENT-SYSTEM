"""WTForms for the administrator area.

Validation runs on the server for every request; HTML5 attributes in the
templates are only a convenience.
"""

from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DecimalField,
    IntegerField,
    PasswordField,
    RadioField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    InputRequired,
    Length,
    NumberRange,
    Optional,
    Regexp,
    ValidationError,
)

from app.extensions import db
from app.models import Department, Doctor, User

PHONE_PATTERN = r"^\+?[0-9][0-9\s\-]{8,14}$"
PASSWORD_PATTERN = r"^(?=.*[A-Za-z])(?=.*\d).+$"


def strip_whitespace(value):
    """Remove leading/trailing spaces before any validator sees the value."""
    return value.strip() if isinstance(value, str) else value


class DoctorFormBase(FlaskForm):
    """Fields shared by 'create doctor' and 'edit doctor'."""

    # --- Account ---------------------------------------------------------
    full_name = StringField(
        "Full name",
        filters=[strip_whitespace],
        validators=[
            DataRequired(message="Enter the doctor's full name."),
            Length(min=3, max=120, message="Name must be between 3 and 120 characters."),
        ],
    )
    email = StringField(
        "Email address",
        filters=[strip_whitespace],
        validators=[
            DataRequired(message="Enter an email address."),
            Email(message="Enter a valid email address."),
            Length(max=150),
        ],
    )
    phone = StringField(
        "Contact number",
        filters=[strip_whitespace],
        validators=[
            Optional(),
            Regexp(PHONE_PATTERN, message="Enter a valid phone number (10-15 digits)."),
        ],
    )

    # --- Professional ----------------------------------------------------
    department_id = SelectField(
        "Department",
        coerce=int,
        validators=[DataRequired(message="Choose a department.")],
    )
    specialization = StringField(
        "Specialization",
        filters=[strip_whitespace],
        validators=[
            DataRequired(message="Enter a specialization."),
            Length(min=2, max=100),
        ],
    )
    qualifications = StringField(
        "Qualifications",
        filters=[strip_whitespace],
        validators=[
            Optional(),
            Length(max=200, message="Keep qualifications under 200 characters."),
        ],
    )
    license_no = StringField(
        "Medical licence number",
        filters=[strip_whitespace],
        validators=[
            DataRequired(message="Enter the licence number."),
            Length(min=3, max=40),
        ],
    )
    experience_years = IntegerField(
        "Years of experience",
        validators=[
            InputRequired(message="Enter the years of experience."),
            NumberRange(min=0, max=70, message="Experience must be between 0 and 70 years."),
        ],
    )
    consultation_fee = DecimalField(
        "Consultation fee (INR)",
        places=2,
        validators=[
            InputRequired(message="Enter the consultation fee."),
            NumberRange(min=0, max=1000000, message="Fee must be between 0 and 10,00,000."),
        ],
    )
    room_no = StringField(
        "Room / chamber",
        filters=[strip_whitespace],
        validators=[Optional(), Length(max=20)],
    )
    bio = TextAreaField(
        "Profile summary",
        filters=[strip_whitespace],
        validators=[Optional(), Length(max=2000)],
    )
    is_available = BooleanField("Available for new bookings", default=True)

    def __init__(self, *args, doctor: Doctor | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        # `doctor` tells the validators which record is being edited, so the
        # doctor's own email/licence are not treated as duplicates.
        self.doctor = doctor
        self.department_id.choices = [
            (department.id, department.name)
            for department in Department.query.order_by(Department.name).all()
        ]

    # --- Uniqueness validation ------------------------------------------
    def validate_email(self, field: StringField) -> None:
        existing = User.query.filter_by(email=field.data.lower()).first()
        if existing and (self.doctor is None or existing.id != self.doctor.user_id):
            raise ValidationError("Another account already uses this email address.")

    def validate_license_no(self, field: StringField) -> None:
        existing = Doctor.query.filter_by(license_no=field.data).first()
        if existing and (self.doctor is None or existing.id != self.doctor.id):
            raise ValidationError("This licence number is already registered.")

    def validate_department_id(self, field: SelectField) -> None:
        if db.session.get(Department, field.data) is None:
            raise ValidationError("Choose a valid department.")


class DoctorCreateForm(DoctorFormBase):
    """Create a doctor together with their login account."""

    password_mode = RadioField(
        "Account password",
        choices=[
            ("generate", "Generate a secure password (shown once after saving)"),
            ("manual", "Set a password myself"),
        ],
        default="generate",
        validators=[DataRequired()],
    )
    password = PasswordField(
        "Password",
        validators=[
            Optional(),
            Length(min=8, max=128, message="Password must be at least 8 characters."),
            Regexp(PASSWORD_PATTERN, message="Password must contain at least one letter and one number."),
        ],
    )
    confirm_password = PasswordField("Confirm password", validators=[Optional()])
    submit = SubmitField("Create doctor")

    def validate(self, extra_validators=None) -> bool:
        if not super().validate(extra_validators):
            return False

        # A manually chosen password must actually be supplied and confirmed;
        # a generated one is created in the service layer.
        if self.password_mode.data == "manual":
            if not (self.password.data or "").strip():
                self.password.errors.append("Enter a password, or switch to automatic generation.")
                return False
            if self.password.data != self.confirm_password.data:
                self.confirm_password.errors.append("Passwords do not match.")
                return False

        return True


class DoctorEditForm(DoctorFormBase):
    """Edit an existing doctor (the password is not changed here)."""

    submit = SubmitField("Save changes")
