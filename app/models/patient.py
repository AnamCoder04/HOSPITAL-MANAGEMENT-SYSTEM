"""Patient model - the medical profile of a user whose role is 'patient'."""

from __future__ import annotations

from datetime import date

from sqlalchemy import event

from app.extensions import db
from app.models.base import TimestampMixin


class Patient(TimestampMixin, db.Model):
    """Patient profile: linked one-to-one to a User, one-to-many appointments."""

    __tablename__ = "patients"
    __table_args__ = (
        db.CheckConstraint(
            "gender IS NULL OR gender IN ('Male', 'Female', 'Other')",
            name="ck_patients_gender",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Human-friendly identifier printed on reports: PAT-000001
    patient_code = db.Column(db.String(20), nullable=False, unique=True, index=True)

    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(10))
    blood_group = db.Column(db.String(5))
    address = db.Column(db.String(255))
    emergency_contact = db.Column(db.String(15))
    allergies = db.Column(db.Text)

    # --- Relationships ---------------------------------------------------
    user = db.relationship("User", back_populates="patient")
    appointments = db.relationship(
        "Appointment",
        back_populates="patient",
        passive_deletes=True,
        order_by="Appointment.appointment_date.desc(), Appointment.appointment_time.desc()",
    )

    # --- Helpers ---------------------------------------------------------
    @staticmethod
    def make_code(user_id: int) -> str:
        """Build the patient code from the (unique) user id."""
        return f"PAT-{user_id:06d}"

    @property
    def full_name(self) -> str:
        return self.user.full_name if self.user else ""

    @property
    def email(self) -> str:
        return self.user.email if self.user else ""

    @property
    def phone(self) -> str | None:
        return self.user.phone if self.user else None

    @property
    def age(self) -> int | None:
        """Age in whole years, or None when no date of birth is recorded."""
        if not self.date_of_birth:
            return None
        today = date.today()
        return (
            today.year
            - self.date_of_birth.year
            - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<Patient {self.patient_code} {self.full_name}>"


@event.listens_for(Patient, "before_insert")
def _assign_patient_code(mapper, connection, target: Patient) -> None:
    """Fill patient_code automatically if the caller did not supply one.

    Runs inside the INSERT flush, so the value is part of the same statement
    and the UNIQUE constraint still protects us.
    """
    if not target.patient_code:
        if target.user_id:
            target.patient_code = Patient.make_code(target.user_id)
        else:  # pragma: no cover - user_id is NOT NULL, so this is defensive
            raise ValueError("A patient must be linked to a user before insertion.")
