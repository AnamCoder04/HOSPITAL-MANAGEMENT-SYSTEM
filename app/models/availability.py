"""DoctorAvailability model - the bookable time slots a doctor publishes."""

from __future__ import annotations

from app.extensions import db
from app.models.base import TimestampMixin
from app.models.appointment import Appointment, AppointmentStatus


class DoctorAvailability(TimestampMixin, db.Model):
    """One consultation slot for one doctor on one date.

    A doctor publishes slots for the next seven days; patients may only book
    a slot that exists here.
    """

    __tablename__ = "doctor_availability"
    __table_args__ = (
        # The same doctor cannot publish two slots starting at the same moment.
        db.UniqueConstraint(
            "doctor_id", "available_date", "start_time",
            name="uq_doctor_availability_slot",
        ),
        db.CheckConstraint("end_time > start_time", name="ck_availability_time_order"),
        db.CheckConstraint("max_patients > 0", name="ck_availability_max_patients"),
    )

    id = db.Column(db.Integer, primary_key=True)

    doctor_id = db.Column(
        db.Integer,
        db.ForeignKey("doctors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    available_date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)

    # How many patients may book this slot (usually 1).
    max_patients = db.Column(db.Integer, nullable=False, default=1)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    # --- Relationships ---------------------------------------------------
    doctor = db.relationship("Doctor", back_populates="availabilities")
    appointments = db.relationship(
        "Appointment",
        back_populates="availability",
        order_by="Appointment.appointment_time",
    )

    # --- Helpers ---------------------------------------------------------
    @property
    def active_appointments(self) -> list[Appointment]:
        """Appointments that still occupy this slot (not cancelled)."""
        return [a for a in self.appointments if a.status != AppointmentStatus.CANCELLED]

    @property
    def booked_count(self) -> int:
        return len(self.active_appointments)

    @property
    def is_full(self) -> bool:
        return self.booked_count >= self.max_patients

    @property
    def slots_left(self) -> int:
        return max(self.max_patients - self.booked_count, 0)

    @property
    def label(self) -> str:
        """e.g. '09:00 - 09:30'."""
        return f"{self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<DoctorAvailability doctor={self.doctor_id} {self.available_date} {self.start_time}>"
