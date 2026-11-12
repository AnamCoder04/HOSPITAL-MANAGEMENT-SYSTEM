"""Department model - the hospital's specialities (Cardiology, ENT, ...)."""

from __future__ import annotations

from app.extensions import db
from app.models.base import TimestampMixin


class Department(TimestampMixin, db.Model):
    """A hospital department. One department employs many doctors."""

    __tablename__ = "departments"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    # One-to-many: department.doctors -> list of Doctor rows.
    doctors = db.relationship(
        "Doctor",
        back_populates="department",
        lazy="selectin",
    )

    # --- Helpers ---------------------------------------------------------
    @property
    def doctor_count(self) -> int:
        return len(self.doctors)

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<Department {self.id} {self.name}>"
