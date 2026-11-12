"""Doctor management rules.

The routes stay thin: everything that decides *whether* something may happen
(password rules, duplicate detection, "is this doctor deletable?") lives here,
so it can be reused and tested in one place.
"""

from __future__ import annotations

import secrets

from sqlalchemy import func

from app.extensions import db
from app.models import Doctor, Role, Treatment, User


def generate_password(length: int = 12) -> str:
    """Random password for a doctor account created by the admin."""
    return secrets.token_urlsafe(length)[:length]


def create_doctor(form, password: str) -> Doctor:
    """Create the login account AND the doctor profile together.

    The user row is what makes the doctor able to sign in; the doctor row holds
    the professional data. Both are committed in one transaction, so a failure
    can never leave an account without a profile.
    """
    user = User(
        full_name=form.full_name.data,
        email=form.email.data,
        phone=form.phone.data or None,
        role=Role.DOCTOR,
        is_active=True,
    )
    user.set_password(password)  # hashed, never stored in plain text

    doctor = Doctor(
        user=user,
        department_id=form.department_id.data,
        specialization=form.specialization.data,
        qualifications=form.qualifications.data or None,
        license_no=form.license_no.data,
        experience_years=form.experience_years.data,
        consultation_fee=form.consultation_fee.data,
        room_no=form.room_no.data or None,
        bio=form.bio.data or None,
        is_available=bool(form.is_available.data),
    )

    db.session.add_all([user, doctor])
    db.session.commit()
    return doctor


def update_doctor(doctor: Doctor, form) -> Doctor:
    """Apply the edit form to the account and the professional profile."""
    doctor.user.full_name = form.full_name.data
    doctor.user.email = form.email.data
    doctor.user.phone = form.phone.data or None

    doctor.department_id = form.department_id.data
    doctor.specialization = form.specialization.data
    doctor.qualifications = form.qualifications.data or None
    doctor.license_no = form.license_no.data
    doctor.experience_years = form.experience_years.data
    doctor.consultation_fee = form.consultation_fee.data
    doctor.room_no = form.room_no.data or None
    doctor.bio = form.bio.data or None
    doctor.is_available = bool(form.is_available.data)

    db.session.commit()
    return doctor


def search_doctors(name: str = "", specialization: str = "") -> list[Doctor]:
    """Search by doctor name (case-insensitive, partial) and exact specialization."""
    query = Doctor.query.join(Doctor.user)

    if name:
        query = query.filter(User.full_name.ilike(f"%{name.strip()}%"))
    if specialization:
        query = query.filter(Doctor.specialization == specialization)

    return query.order_by(Doctor.created_at.desc()).all()


def specializations() -> list[str]:
    """Distinct specializations already in use, for the filter dropdown."""
    rows = (
        db.session.query(Doctor.specialization)
        .distinct()
        .order_by(Doctor.specialization)
        .all()
    )
    return [row[0] for row in rows]


def toggle_doctor_active(doctor: Doctor) -> bool:
    """Enable/disable the doctor's login. Returns the new state."""
    doctor.user.is_active = not doctor.user.is_active
    db.session.commit()
    return doctor.user.is_active


def doctor_history(doctor: Doctor) -> dict:
    """Counts that decide whether a doctor may be deleted."""
    appointment_count = len(doctor.appointments)
    treatment_count = (
        db.session.query(func.count(Treatment.id))
        .filter(Treatment.doctor_id == doctor.id)
        .scalar()
        or 0
    )
    return {"appointments": appointment_count, "treatments": treatment_count}


def can_delete_doctor(doctor: Doctor) -> bool:
    """A doctor with any appointment or treatment history must be deactivated.

    Deleting would destroy part of a patient's medical record, so the rule is
    enforced here and not only in the template.
    """
    history = doctor_history(doctor)
    return history["appointments"] == 0 and history["treatments"] == 0


def busy_doctor_ids() -> set[int]:
    """Ids of doctors that already have appointments (for the list page)."""
    rows = db.session.query(Doctor.id).join(Doctor.appointments).distinct().all()
    return {row[0] for row in rows}


def delete_doctor(doctor: Doctor) -> None:
    """Delete a doctor *only* when there is no history. Raises otherwise."""
    if not can_delete_doctor(doctor):
        raise ValueError(
            "This doctor has appointment or treatment history and cannot be deleted. "
            "Deactivate the account instead."
        )
    # Deleting the user cascades to the doctor profile and its availability.
    db.session.delete(doctor.user)
    db.session.commit()
