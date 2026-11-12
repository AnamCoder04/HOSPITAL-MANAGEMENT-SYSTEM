"""User model - one authentication record per person, whatever their role.

Design: authentication columns live here; role-specific columns live in the
`doctors` and `patients` tables, joined one-to-one on user_id.
"""

from __future__ import annotations

from flask_login import UserMixin
from sqlalchemy.orm import validates
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, login_manager
from app.models.base import TimestampMixin


class Role:
    """The three roles in the system (stored as short lowercase strings)."""

    ADMIN = "admin"
    DOCTOR = "doctor"
    PATIENT = "patient"

    ALL = (ADMIN, DOCTOR, PATIENT)
    LABELS = {ADMIN: "Administrator", DOCTOR: "Doctor", PATIENT: "Patient"}


class User(UserMixin, TimestampMixin, db.Model):
    """A login account: admin, doctor or patient."""

    __tablename__ = "users"
    __table_args__ = (
        db.CheckConstraint(
            "role IN ('admin', 'doctor', 'patient')",
            name="ck_users_role",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(10), nullable=False, default=Role.PATIENT, index=True)
    phone = db.Column(db.String(15))

    # Account state -------------------------------------------------------
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_blacklisted = db.Column(db.Boolean, nullable=False, default=False)
    blacklist_reason = db.Column(db.String(255))
    last_login = db.Column(db.DateTime)

    # One-to-one profiles -------------------------------------------------
    doctor = db.relationship(
        "Doctor",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    patient = db.relationship(
        "Patient",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # --- Password handling ----------------------------------------------
    def set_password(self, raw_password: str) -> None:
        """Hash and store a password. The plain text is never saved."""
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        """Compare a typed password with the stored hash."""
        return check_password_hash(self.password_hash, raw_password)

    # --- Convenience properties used by templates and guards -------------
    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    @property
    def is_doctor(self) -> bool:
        return self.role == Role.DOCTOR

    @property
    def is_patient(self) -> bool:
        return self.role == Role.PATIENT

    @property
    def role_label(self) -> str:
        return Role.LABELS.get(self.role, self.role.title())

    @property
    def can_log_in(self) -> bool:
        """A deactivated or blacklisted account may not sign in."""
        return self.is_active and not self.is_blacklisted

    @property
    def initials(self) -> str:
        """Up to two initials, for avatar circles in the UI."""
        parts = [p for p in (self.full_name or "").split() if p]
        return "".join(p[0].upper() for p in parts[:2]) or "?"

    # --- Validation ------------------------------------------------------
    @validates("email")
    def _normalise_email(self, key: str, value: str) -> str:
        """Store e-mails lowercase so logins are case-insensitive."""
        if not value or "@" not in value:
            raise ValueError("A valid e-mail address is required.")
        return value.strip().lower()

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<User {self.id} {self.email} ({self.role})>"


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    """Turn the id stored in the session cookie back into a User object."""
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None
