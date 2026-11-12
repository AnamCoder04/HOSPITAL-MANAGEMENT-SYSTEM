"""Database models.

Importing this package imports every model, which is what makes
`db.create_all()` aware of all seven tables. Keep the order: models that are
referenced by string ("Doctor") only need to exist by the time SQLAlchemy
configures the mappers, but importing User first documents the dependency
chain and avoids surprises in a fresh interpreter.
"""

from app.models.base import TimestampMixin, utcnow
from app.models.user import Role, User, load_user
from app.models.department import Department
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.appointment import Appointment, AppointmentStatus
from app.models.availability import DoctorAvailability
from app.models.treatment import Treatment

__all__ = [
    "TimestampMixin",
    "utcnow",
    "Role",
    "User",
    "load_user",
    "Department",
    "Doctor",
    "Patient",
    "Appointment",
    "AppointmentStatus",
    "DoctorAvailability",
    "Treatment",
]
