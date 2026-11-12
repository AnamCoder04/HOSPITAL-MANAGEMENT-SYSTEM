"""Doctor model - the professional profile of a user whose role is 'doctor'."""

from __future__ import annotations

from decimal import Decimal

from app.extensions import db
from app.models.base import TimestampMixin


class Doctor(TimestampMixin, db.Model):
    """Doctor profile: linked one-to-one to a User, many-to-one to Department."""

    __tablename__ = "doctors"
    __table_args__ = (
        db.CheckConstraint("experience_years >= 0", name="ck_doctors_experience"),
        db.CheckConstraint("consultation_fee >= 0", name="ck_doctors_fee"),
    )

    id = db.Column(db.Integer, primary_key=True)

    # One-to-one with users. UNIQUE guarantees an account has at most one
    # doctor profile; ON DELETE CASCADE removes the profile with the account.
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Many doctors belong to one department. RESTRICT stops a department
    # from being deleted while doctors still reference it.
    department_id = db.Column(
        db.Integer,
        db.ForeignKey("departments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    specialization = db.Column(db.String(100), nullable=False, index=True)
    qualifications = db.Column(db.String(200))  # e.g. MBBS, MD (Cardiology)
    license_no = db.Column(db.String(40), nullable=False, unique=True)
    experience_years = db.Column(db.Integer, nullable=False, default=0)
    consultation_fee = db.Column(db.Numeric(8, 2), nullable=False, default=Decimal("0.00"))
    room_no = db.Column(db.String(20))
    bio = db.Column(db.Text)

    # Admin-controlled switch: False hides the doctor from booking.
    is_available = db.Column(db.Boolean, nullable=False, default=True)

    # --- Relationships ---------------------------------------------------
    user = db.relationship("User", back_populates="doctor")
    department = db.relationship("Department", back_populates="doctors")

    availabilities = db.relationship(
        "DoctorAvailability",
        back_populates="doctor",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="DoctorAvailability.available_date, DoctorAvailability.start_time",
    )
    appointments = db.relationship(
        "Appointment",
        back_populates="doctor",
        passive_deletes=True,
        order_by="Appointment.appointment_date.desc(), Appointment.appointment_time.desc()",
    )
    treatments = db.relationship("Treatment", back_populates="doctor", passive_deletes=True)

    # --- Delegated identity fields --------------------------------------
    # The name/email/phone live on User; these read-only shortcuts keep
    # templates simple: {{ doctor.full_name }} instead of doctor.user.full_name.
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
    def is_bookable(self) -> bool:
        """Bookable only when the admin enabled the doctor and the account is healthy."""
        return bool(
            self.is_available
            and self.user
            and self.user.is_active
            and not self.user.is_blacklisted
        )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<Doctor {self.id} {self.full_name} - {self.specialization}>"
