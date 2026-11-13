"""WTForms for the administrator area.

Validation runs on the server for every request; HTML5 attributes in the
templates are only a convenience.
"""

from __future__ import annotations

import re
from datetime import date

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
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

from sqlalchemy import func

from app.extensions import db
from app.models import Department, Doctor, Patient, User

PHONE_PATTERN = r"^\+?[0-9][0-9\s\-]{8,14}$"
PASSWORD_PATTERN = r"^(?=.*[A-Za-z])(?=.*\d).+$"
PATIENT_CODE_PATTERN = r"^(?:PAT-)?\d{1,9}$"

GENDER_CHOICES = [
    ("", "Not specified"),
    ("Male", "Male"),
    ("Female", "Female"),
    ("Other", "Other"),
]

BLOOD_GROUP_CHOICES = [
    ("", "Not recorded"),
    ("A+", "A+"), ("A-", "A-"),
    ("B+", "B+"), ("B-", "B-"),
    ("AB+", "AB+"), ("AB-", "AB-"),
    ("O+", "O+"), ("O-", "O-"),
]


def strip_whitespace(value):
    """Remove leading/trailing spaces before any validator sees the value."""
    return value.strip() if isinstance(value, str) else value


def collapse_spaces(value):
    """Turn 'A   B' into 'A B' so the same name cannot be stored twice."""
    return " ".join(value.split()) if isinstance(value, str) else value


# ---------------------------------------------------------------------------
# Departments
# ---------------------------------------------------------------------------
class DepartmentForm(FlaskForm):
    """Create or edit a hospital department."""

    name = StringField(
        "Department name",
        filters=[strip_whitespace, collapse_spaces],
        validators=[
            DataRequired(message="Enter the department name."),
            Length(min=2, max=80, message="Name must be between 2 and 80 characters."),
        ],
    )
    description = TextAreaField(
        "Description",
        filters=[strip_whitespace],
        validators=[
            Optional(),
            Length(max=1000, message="Keep the description under 1000 characters."),
        ],
    )
    is_active = BooleanField("Accepting doctor assignments", default=True)
    submit = SubmitField("Save department")

    def __init__(self, *args, department: Department | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        # Used by both validators below so a department keeps its own name and
        # state while editing.
        self.department = department

    def validate_name(self, field: StringField) -> None:
        """Names are unique case-insensitively, ignoring the edited record."""
        existing = Department.query.filter(
            func.lower(Department.name) == field.data.lower()
        ).first()
        if existing and (self.department is None or existing.id != self.department.id):
            raise ValidationError("A department with this name already exists.")

    def validate_is_active(self, field: BooleanField) -> None:
        """Refuse to retire a department that still has active doctors."""
        if self.department is None or not self.department.is_active or field.data:
            return
        if self.department.active_doctor_count:
            raise ValidationError(
                f"{self.department.active_doctor_count} active doctor(s) still work here. "
                "Reassign or deactivate them before retiring the department."
            )


class DepartmentSearchForm(FlaskForm):
    """GET filter form for the department list."""

    class Meta:
        csrf = False

    q = StringField(
        "Search departments",
        filters=[strip_whitespace],
        validators=[Optional(), Length(max=80, message="Search text is too long.")],
    )
    status = SelectField(
        "Status",
        choices=[("all", "All departments"), ("active", "Active only"), ("inactive", "Retired only")],
        default="all",
        validators=[Optional()],
    )
    submit = SubmitField("Search")


# ---------------------------------------------------------------------------
# Doctors
# ---------------------------------------------------------------------------
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

        # Only active departments can be assigned. A doctor already working in
        # a department that was later retired keeps it selectable, so editing
        # their other details does not force a reassignment.
        departments = Department.query.filter_by(is_active=True).order_by(Department.name).all()
        current = self.doctor.department if self.doctor is not None else None
        if current is not None and not current.is_active:
            departments.append(current)
            departments.sort(key=lambda item: item.name)

        self.department_id.choices = [(item.id, item.name) for item in departments]

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
        """The department must exist *and* still accept doctor assignments."""
        department = db.session.get(Department, field.data)
        if department is None:
            raise ValidationError("Choose a valid department.")

        current_id = self.doctor.department_id if self.doctor is not None else None
        if not department.is_active and department.id != current_id:
            raise ValidationError("That department has been retired. Choose an active department.")


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


# ---------------------------------------------------------------------------
# Patients
# ---------------------------------------------------------------------------
class PatientSearchForm(FlaskForm):
    """GET filter form for the patient list (no CSRF: it changes nothing)."""

    class Meta:
        csrf = False

    q = StringField(
        "Search by name",
        filters=[strip_whitespace],
        validators=[Optional(), Length(max=120, message="Search text is too long.")],
    )
    patient_id = StringField(
        "Patient ID",
        filters=[strip_whitespace],
        validators=[
            Optional(),
            Regexp(
                PATIENT_CODE_PATTERN,
                flags=re.IGNORECASE,
                message="Use the format PAT-000123 (or just the number).",
            ),
        ],
    )
    phone = StringField(
        "Contact number",
        filters=[strip_whitespace],
        validators=[
            Optional(),
            Regexp(r"^[0-9+\s\-]{3,20}$", message="Digits, spaces, + and - only."),
        ],
    )
    submit = SubmitField("Search")


class PatientEditForm(FlaskForm):
    """Edit a patient's account and medical profile.

    The patient ID is deliberately not editable: it is the identifier printed
    on reports and referenced by appointments.
    """

    full_name = StringField(
        "Full name",
        filters=[strip_whitespace, collapse_spaces],
        validators=[
            DataRequired(message="Enter the patient's full name."),
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
            DataRequired(message="Enter a contact number."),
            Regexp(PHONE_PATTERN, message="Enter a valid phone number (10-15 digits)."),
        ],
    )

    date_of_birth = DateField(
        "Date of birth",
        format="%Y-%m-%d",
        validators=[Optional()],
    )
    gender = SelectField("Gender", choices=GENDER_CHOICES, validators=[Optional()])
    blood_group = SelectField("Blood group", choices=BLOOD_GROUP_CHOICES, validators=[Optional()])
    address = StringField(
        "Address",
        filters=[strip_whitespace],
        validators=[Optional(), Length(max=255, message="Keep the address under 255 characters.")],
    )
    emergency_contact = StringField(
        "Emergency contact",
        filters=[strip_whitespace],
        validators=[
            Optional(),
            Regexp(PHONE_PATTERN, message="Enter a valid emergency phone number."),
        ],
    )
    allergies = TextAreaField(
        "Allergies / chronic conditions",
        filters=[strip_whitespace],
        validators=[Optional(), Length(max=1000, message="Keep this under 1000 characters.")],
    )

    submit = SubmitField("Save changes")

    def __init__(self, *args, patient: Patient | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        # Used by the uniqueness check so a patient keeps their own email.
        self.patient = patient

    def validate_email(self, field: StringField) -> None:
        existing = User.query.filter_by(email=field.data.lower()).first()
        if existing and (self.patient is None or existing.id != self.patient.user_id):
            raise ValidationError("Another account already uses this email address.")

    def validate_date_of_birth(self, field: DateField) -> None:
        value = field.data
        if value is None:
            return
        if value > date.today():
            raise ValidationError("Date of birth cannot be in the future.")
        if value < date(1900, 1, 1):
            raise ValidationError("Enter a date of birth after 1 January 1900.")
