"""Appointment model - the link between one patient and one doctor."""

from __future__ import annotations

from sqlalchemy import event

from app.extensions import db
from app.models.base import TimestampMixin


class AppointmentStatus:
    """The only three states an appointment can be in."""

    BOOKED = "booked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

    ALL = (BOOKED, COMPLETED, CANCELLED)

    LABELS = {BOOKED: "Booked", COMPLETED: "Completed", CANCELLED: "Cancelled"}

    # Bootstrap-style badge classes, used by the templates from Task 5 on.
    BADGE_CLASSES = {
        BOOKED: "badge-soft-blue",
        COMPLETED: "badge-soft-teal",
        CANCELLED: "badge-soft-red",
    }

    # Statuses that still hold the doctor's time slot.
    BLOCKING = (BOOKED, COMPLETED)


class Appointment(TimestampMixin, db.Model):
    """A booking of one patient with one doctor at one date and time."""

    __tablename__ = "appointments"
    __table_args__ = (
        db.CheckConstraint(
            "status IN ('booked', 'completed', 'cancelled')",
            name="ck_appointments_status",
        ),
        # ------------------------------------------------------------------
        # The double-booking rule.
        #
        # A plain UNIQUE(doctor_id, appointment_date, appointment_time) would
        # also block re-booking a slot after a cancellation. This PARTIAL
        # unique index only indexes rows whose status is not 'cancelled',
        # so cancelled appointments never occupy a slot while the database
        # itself refuses a second active booking at the same moment.
        # ------------------------------------------------------------------
        db.Index(
            "uq_active_doctor_slot",
            "doctor_id", "appointment_date", "appointment_time",
            unique=True,
            sqlite_where=db.text("status != 'cancelled'"),
        ),
        # The same patient cannot hold two active bookings for the same
        # moment with the same doctor. Cancelled rows are excluded, so a
        # patient can book again after cancelling.
        db.Index(
            "uq_active_patient_slot",
            "patient_id", "doctor_id", "appointment_date", "appointment_time",
            unique=True,
            sqlite_where=db.text("status != 'cancelled'"),
        ),
        db.Index("ix_appointments_doctor_date", "doctor_id", "appointment_date"),
        db.Index("ix_appointments_patient_date", "patient_id", "appointment_date"),
    )

    id = db.Column(db.Integer, primary_key=True)

    patient_id = db.Column(
        db.Integer,
        db.ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    doctor_id = db.Column(
        db.Integer,
        db.ForeignKey("doctors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # The published slot that was booked. SET NULL keeps the appointment if
    # the doctor later removes the slot from their availability.
    availability_id = db.Column(
        db.Integer,
        db.ForeignKey("doctor_availability.id", ondelete="SET NULL"),
    )

    appointment_date = db.Column(db.Date, nullable=False, index=True)
    appointment_time = db.Column(db.Time, nullable=False)

    status = db.Column(
        db.String(12),
        nullable=False,
        default=AppointmentStatus.BOOKED,
        index=True,
    )

    reason = db.Column(db.Text)          # patient's complaint, set when booking
    cancel_reason = db.Column(db.Text)   # filled when someone cancels

    # --- Relationships ---------------------------------------------------
    patient = db.relationship("Patient", back_populates="appointments")
    doctor = db.relationship("Doctor", back_populates="appointments")
    availability = db.relationship("DoctorAvailability", back_populates="appointments")

    # One-to-one: an appointment has at most one clinical record.
    treatment = db.relationship(
        "Treatment",
        back_populates="appointment",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # --- Status helpers --------------------------------------------------
    @property
    def status_label(self) -> str:
        return AppointmentStatus.LABELS.get(self.status, self.status.title())

    @property
    def status_badge_class(self) -> str:
        return AppointmentStatus.BADGE_CLASSES.get(self.status, "badge-soft-blue")

    @property
    def is_booked(self) -> bool:
        return self.status == AppointmentStatus.BOOKED

    @property
    def is_completed(self) -> bool:
        return self.status == AppointmentStatus.COMPLETED

    @property
    def is_cancelled(self) -> bool:
        return self.status == AppointmentStatus.CANCELLED

    @property
    def is_editable(self) -> bool:
        """Only a booked appointment may be rescheduled or cancelled."""
        return self.is_booked

    @property
    def slot_label(self) -> str:
        return f"{self.appointment_time.strftime('%H:%M')}"

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return (
            f"<Appointment {self.id} patient={self.patient_id} doctor={self.doctor_id} "
            f"{self.appointment_date} {self.appointment_time} [{self.status}]>"
        )


@event.listens_for(Appointment, "before_delete")
def _protect_medical_history(mapper, connection, target: Appointment) -> None:
    """Never allow a completed appointment to be deleted.

    Completed consultations are part of the patient's medical history.
    Cancelling is a status change, not a deletion, so no legitimate flow
    needs this - the guard exists to make the rule impossible to break by
    accident from a future view or a `flask shell` session.
    """
    if target.status == AppointmentStatus.COMPLETED:
        raise ValueError(
            "Completed appointments are part of the medical history and cannot be deleted. "
            "Cancel or deactivate instead."
        )
