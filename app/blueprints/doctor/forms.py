"""WTForms for the doctor portal."""

from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
    TimeField,
)
from wtforms.validators import DataRequired, InputRequired, Length, NumberRange, Optional

from app.models import AppointmentStatus


class AvailabilityForm(FlaskForm):
    """Publish a consultation slot for one of the next seven days.

    Format checks happen here; the seven-day window, working hours, overlap
    and capacity rules are enforced by `availability_service` because they
    need the doctor's other slots and appointments.
    """

    available_date = DateField(
        "Date",
        format="%Y-%m-%d",
        validators=[DataRequired(message="Choose a date.")],
    )
    start_time = TimeField(
        "Start time",
        format="%H:%M",
        validators=[DataRequired(message="Choose a start time.")],
    )
    end_time = TimeField(
        "End time",
        format="%H:%M",
        validators=[DataRequired(message="Choose an end time.")],
    )
    max_patients = IntegerField(
        "Patients",
        default=1,
        validators=[
            InputRequired(message="Enter how many patients this slot takes."),
            NumberRange(min=1, max=20, message="A slot can take between 1 and 20 patients."),
        ],
    )
    submit = SubmitField("Publish slot")


class AvailabilityEditForm(AvailabilityForm):
    """Same fields, different button label."""

    submit = SubmitField("Save changes")


class TreatmentForm(FlaskForm):
    """The clinical record for one completed appointment.

    ``diagnosis`` is the only mandatory part; prescriptions, plans and notes
    are free text on purpose - a college project should not pretend to model
    drug dosage rules. ``follow_up_date`` is checked against the visit date by
    ``treatment_service`` because that needs the appointment.
    """

    diagnosis = TextAreaField(
        "Diagnosis",
        validators=[
            DataRequired(message="Enter the diagnosis."),
            Length(min=5, max=1000, message="The diagnosis must be 5-1000 characters."),
        ],
    )
    prescription = TextAreaField(
        "Prescription",
        validators=[Optional(), Length(max=2000, message="Keep the prescription under 2000 characters.")],
    )
    treatment_plan = TextAreaField(
        "Treatment plan",
        validators=[Optional(), Length(max=2000, message="Keep the plan under 2000 characters.")],
    )
    notes = TextAreaField(
        "Doctor's notes",
        validators=[Optional(), Length(max=2000, message="Keep the notes under 2000 characters.")],
    )
    follow_up_date = DateField(
        "Follow-up date",
        format="%Y-%m-%d",
        validators=[Optional()],
    )
    submit = SubmitField("Save treatment record")


class AppointmentFilterForm(FlaskForm):
    """GET filter form for a doctor's own appointment list."""

    class Meta:
        csrf = False

    view = SelectField(
        "View",
        choices=[
            ("upcoming", "Upcoming"),
            ("today", "Today"),
            ("week", "This week"),
            ("all", "All appointments"),
        ],
        default="upcoming",
        validators=[Optional()],
    )
    status = SelectField(
        "Status",
        choices=[("", "All statuses")] + [(value, value.title()) for value in AppointmentStatus.ALL],
        validators=[Optional()],
    )
    q = StringField(
        "Patient name",
        filters=[lambda value: value.strip() if isinstance(value, str) else value],
        validators=[Optional(), Length(max=120, message="Search text is too long.")],
    )
    submit = SubmitField("Apply")
