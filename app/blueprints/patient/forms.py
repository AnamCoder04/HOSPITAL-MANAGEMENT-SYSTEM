"""WTForms for the patient portal."""

from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, Optional

from app.services import availability_service


class DoctorSearchForm(FlaskForm):
    """GET filter form for doctor search (no CSRF: it changes nothing).

    Choices are loaded from the database in `__init__`, so an edited query
    string cannot inject a specialization or department that does not exist.
    """

    class Meta:
        csrf = False

    name = StringField(
        "Doctor name",
        filters=[lambda value: value.strip() if isinstance(value, str) else value],
        validators=[Optional(), Length(max=120, message="Search text is too long.")],
    )
    specialization = SelectField(
        "Specialization",
        choices=[("", "All specializations")],
        validators=[Optional()],
    )
    department_id = SelectField(
        "Department",
        coerce=int,
        choices=[(0, "All departments")],
        validators=[Optional()],
    )
    submit = SubmitField("Search")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.specialization.choices = [("", "All specializations")] + [
            (value, value) for value in availability_service.specialization_options()
        ]
        self.department_id.choices = [(0, "All departments")] + [
            (department.id, department.name)
            for department in availability_service.department_options()
        ]


class RescheduleForm(FlaskForm):
    """Pick one of the doctor's currently open slots.

    The route fills `slot_id.choices` with the slots that are actually open,
    and `appointment_service.reschedule_appointment` re-checks the chosen slot
    so a hand-edited request cannot move an appointment onto a full or past
    slot.
    """

    slot_id = SelectField(
        "New time",
        coerce=int,
        choices=[],
        validators=[DataRequired(message="Choose a new time.")],
    )
    submit = SubmitField("Confirm new time")
