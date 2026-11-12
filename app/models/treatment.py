"""Treatment model - the clinical record written by the doctor."""

from __future__ import annotations

from app.extensions import db
from app.models.base import TimestampMixin


class Treatment(TimestampMixin, db.Model):
    """Diagnosis, prescription and plan for exactly one appointment.

    UNIQUE(appointment_id) makes this a strict one-to-one: one consultation
    produces one clinical record, so a doctor can never write two conflicting
    diagnoses for the same visit.
    """

    __tablename__ = "treatments"

    id = db.Column(db.Integer, primary_key=True)

    appointment_id = db.Column(
        db.Integer,
        db.ForeignKey("appointments.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    # Who wrote the record - kept for auditability even if the appointment's
    # doctor relationship is ever re-pointed.
    doctor_id = db.Column(
        db.Integer,
        db.ForeignKey("doctors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    diagnosis = db.Column(db.Text, nullable=False)
    prescription = db.Column(db.Text)
    treatment_plan = db.Column(db.Text)
    notes = db.Column(db.Text)
    follow_up_date = db.Column(db.Date)

    # --- Relationships ---------------------------------------------------
    appointment = db.relationship("Appointment", back_populates="treatment")
    doctor = db.relationship("Doctor", back_populates="treatments")

    # --- Helpers ---------------------------------------------------------
    @property
    def patient(self):
        """Shortcut: the patient this record belongs to."""
        return self.appointment.patient if self.appointment else None

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<Treatment {self.id} appointment={self.appointment_id}>"
