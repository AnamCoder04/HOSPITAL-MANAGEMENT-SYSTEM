"""WTForms for the doctor portal."""

from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import DateField, IntegerField, SubmitField, TimeField
from wtforms.validators import DataRequired, InputRequired, NumberRange


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
