"""Department management rules (Task 9).

Departments are the hospital's specialities. They are never deleted: a doctor
row and, through it, the whole appointment history point at a department, so
removing the row would break medical records. "Retiring" a department means
deactivating it, which only hides it from new doctor assignments.
"""

from __future__ import annotations

from sqlalchemy import or_

from app.extensions import db
from app.models import Appointment, Department, Doctor, User


def search_departments(term: str = "", status: str = "all") -> list[Department]:
    """Departments filtered by name/description text and active state."""
    query = Department.query

    if term:
        like = f"%{term.strip()}%"
        query = query.filter(
            or_(Department.name.ilike(like), Department.description.ilike(like))
        )

    if status == "active":
        query = query.filter(Department.is_active.is_(True))
    elif status == "inactive":
        query = query.filter(Department.is_active.is_(False))

    return query.order_by(Department.name).all()


def create_department(form) -> Department:
    """Create a department from a validated form."""
    department = Department(
        name=form.name.data,
        description=form.description.data or None,
        is_active=bool(form.is_active.data),
    )
    db.session.add(department)
    db.session.commit()
    return department


def update_department(department: Department, form) -> Department:
    """Rename a department or edit its description.

    Renaming is safe: doctors reference the department by id, so every
    appointment and treatment keeps pointing at the same record.
    """
    wants_active = bool(form.is_active.data)
    if department.is_active and not wants_active and not can_deactivate(department):
        # The form validator catches this first; the guard keeps the rule true
        # for any other caller (shell, future API).
        raise ValueError(
            f"{department.name} still has {department.active_doctor_count} active "
            "doctor(s). Reassign or deactivate them before retiring the department."
        )

    department.name = form.name.data
    department.description = form.description.data or None
    department.is_active = wants_active
    db.session.commit()
    return department


def can_deactivate(department: Department) -> bool:
    """A department can only be retired once no active doctor works in it."""
    return department.active_doctor_count == 0


def toggle_department_active(department: Department) -> bool:
    """Activate or retire a department. Returns the new state.

    Raises ValueError when retiring would leave active doctors in a hidden
    department - they must be reassigned or deactivated first.
    """
    if department.is_active and not can_deactivate(department):
        raise ValueError(
            f"{department.name} still has {department.active_doctor_count} active "
            "doctor(s). Reassign or deactivate them before retiring the department."
        )

    department.is_active = not department.is_active
    db.session.commit()
    return department.is_active


def department_doctors(department: Department) -> list[Doctor]:
    """Doctors registered under a department, alphabetical by name."""
    return (
        Doctor.query.filter_by(department_id=department.id)
        .join(Doctor.user)
        .order_by(User.full_name)
        .all()
    )


def department_stats(department: Department) -> dict:
    """Counts for the department page; all from SQL."""
    appointments = (
        Appointment.query.join(Appointment.doctor)
        .filter(Doctor.department_id == department.id)
        .count()
    )

    return {
        "doctors": department.doctor_count,
        "active_doctors": department.active_doctor_count,
        "specializations": len(department.specializations),
        "appointments": appointments,
    }
