"""Doctor availability rules (Task 10).

A doctor publishes consultation slots for the next seven calendar days.
Patients can only book a slot that exists here, is still open and has room,
which is what makes "no booking outside the published slots" true.

The rules that matter live in this module, not in the views:

  * the seven-day window and working hours
  * no overlapping slots for one doctor
  * a slot with bookings keeps its date and time (and cannot be hidden or
    deleted) until those appointments are cancelled
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import (
    Appointment,
    AppointmentStatus,
    Department,
    Doctor,
    DoctorAvailability,
    Patient,
    Role,
    User,
)

WINDOW_DAYS = 7
DAY_START = time(8, 0)
DAY_END = time(21, 0)
MIN_MINUTES_PER_PATIENT = 5

# Label + badge class for each slot state, for templates.
STATUS_META = {
    "open": ("Open", "badge-soft-teal"),
    "full": ("Full", "badge-soft-amber"),
    "past": ("Passed", "badge-soft-blue"),
    "hidden": ("Hidden", "badge-soft-amber"),
}


# ---------------------------------------------------------------------------
# The seven-day window
# ---------------------------------------------------------------------------
def week_dates(start: date | None = None) -> list[date]:
    """Today plus the six following days."""
    start = start or date.today()
    return [start + timedelta(days=offset) for offset in range(WINDOW_DAYS)]


def window_bounds(start: date | None = None) -> tuple[date, date]:
    days = week_dates(start)
    return days[0], days[-1]


def is_within_window(day: date, start: date | None = None) -> bool:
    first, last = window_bounds(start)
    return first <= day <= last


def _is_past(slot: DoctorAvailability) -> bool:
    """A slot is past once its start time has gone by."""
    today = date.today()
    if slot.available_date < today:
        return True
    return slot.available_date == today and slot.start_time <= datetime.now().time()


def _duration_minutes(start: time, end: time) -> int:
    return int(
        (datetime.combine(date.min, end) - datetime.combine(date.min, start)).total_seconds() // 60
    )


def slot_status(slot: DoctorAvailability) -> str:
    if not slot.is_active:
        return "hidden"
    if _is_past(slot):
        return "past"
    if slot.is_full:
        return "full"
    return "open"


# ---------------------------------------------------------------------------
# Reading slots
# ---------------------------------------------------------------------------
def slots_by_date(doctor: Doctor, start: date | None = None) -> dict[date, list[DoctorAvailability]]:
    """Every slot this doctor published in the window, grouped by day."""
    days = week_dates(start)
    slots = (
        DoctorAvailability.query.filter(
            DoctorAvailability.doctor_id == doctor.id,
            DoctorAvailability.available_date.in_(days),
        )
        .order_by(DoctorAvailability.available_date, DoctorAvailability.start_time)
        .all()
    )

    grouped: dict[date, list[DoctorAvailability]] = {day: [] for day in days}
    for slot in slots:
        grouped[slot.available_date].append(slot)
    return grouped


def patient_slots_by_date(doctor: Doctor) -> dict[date, list[DoctorAvailability]]:
    """Only what a patient may see: active slots that have not started yet."""
    grouped = {day: [] for day in week_dates()}
    for day, slots in slots_by_date(doctor).items():
        grouped[day] = [
            slot for slot in slots if slot.is_active and not _is_past(slot)
        ]
    return grouped


def statuses_for(slots: list[DoctorAvailability]) -> dict[int, str]:
    return {slot.id: slot_status(slot) for slot in slots}


def open_slot_count(doctor: Doctor) -> int:
    """How many slots a patient could book right now - used by the doctor list."""
    return sum(
        1
        for slots in patient_slots_by_date(doctor).values()
        for slot in slots
        if not slot.is_full
    )


# ---------------------------------------------------------------------------
# Validation shared by create and edit
# ---------------------------------------------------------------------------
def _validate_form_values(day: date, start: time, end: time, capacity: int, booked: int = 0) -> None:
    if day is None or start is None or end is None:
        raise ValueError("Enter a date, a start time and an end time.")

    first, last = window_bounds()
    if not is_within_window(day):
        raise ValueError(
            f"Availability can only be published for the next {WINDOW_DAYS} days "
            f"({first.strftime('%d %b')} to {last.strftime('%d %b')})."
        )

    if start < DAY_START or end > DAY_END:
        raise ValueError(
            f"Slots must fall between {DAY_START.strftime('%H:%M')} and "
            f"{DAY_END.strftime('%H:%M')}."
        )

    if end <= start:
        raise ValueError("The end time must be after the start time.")

    if day == date.today() and start <= datetime.now().time():
        raise ValueError("That start time has already passed today. Choose a later time.")

    if capacity is None or capacity < 1 or capacity > 20:
        raise ValueError("A slot can take between 1 and 20 patients.")

    if capacity < booked:
        raise ValueError(
            f"{booked} appointment(s) are already booked, so the capacity cannot be "
            f"lower than {booked}."
        )

    minutes = _duration_minutes(start, end)
    if minutes // capacity < MIN_MINUTES_PER_PATIENT:
        raise ValueError(
            f"Each patient needs at least {MIN_MINUTES_PER_PATIENT} minutes. "
            "Lengthen the slot or reduce the number of patients."
        )


def _overlapping_slot(
    doctor_id: int, day: date, start: time, end: time, exclude_id: int | None = None
) -> DoctorAvailability | None:
    query = DoctorAvailability.query.filter(
        DoctorAvailability.doctor_id == doctor_id,
        DoctorAvailability.available_date == day,
        DoctorAvailability.start_time < end,
        DoctorAvailability.end_time > start,
    )
    if exclude_id is not None:
        query = query.filter(DoctorAvailability.id != exclude_id)
    return query.order_by(DoctorAvailability.start_time).first()


# ---------------------------------------------------------------------------
# Writing slots
# ---------------------------------------------------------------------------
def create_slot(doctor: Doctor, form) -> DoctorAvailability:
    """Publish a new slot after window, hour, capacity and overlap checks."""
    day, start, end = form.available_date.data, form.start_time.data, form.end_time.data
    capacity = form.max_patients.data or 1

    _validate_form_values(day, start, end, capacity)

    clash = _overlapping_slot(doctor.id, day, start, end)
    if clash is not None:
        raise ValueError(
            f"This overlaps your existing {clash.label} slot on "
            f"{day.strftime('%d %b')}. Edit that slot instead."
        )

    slot = DoctorAvailability(
        doctor_id=doctor.id,
        available_date=day,
        start_time=start,
        end_time=end,
        max_patients=capacity,
        is_active=True,
    )
    db.session.add(slot)
    db.session.commit()
    return slot


def update_slot(slot: DoctorAvailability, form) -> DoctorAvailability:
    """Edit a slot, refusing changes that would break booked appointments."""
    day, start, end = form.available_date.data, form.start_time.data, form.end_time.data
    capacity = form.max_patients.data or 1
    booked = slot.booked_count

    _validate_form_values(day, start, end, capacity, booked)

    if booked and (
        day != slot.available_date or start != slot.start_time or end != slot.end_time
    ):
        raise ValueError(
            f"{booked} appointment(s) are already booked in this slot, so its date and "
            "time cannot change. Cancel those appointments first, or add a new slot."
        )

    if not slot.is_active and capacity < slot.booked_count:
        raise ValueError("A hidden slot cannot take fewer patients than it already has booked.")

    clash = _overlapping_slot(slot.doctor_id, day, start, end, exclude_id=slot.id)
    if clash is not None:
        raise ValueError(
            f"This would overlap your {clash.label} slot on {day.strftime('%d %b')}."
        )

    slot.available_date = day
    slot.start_time = start
    slot.end_time = end
    slot.max_patients = capacity
    db.session.commit()
    return slot


def delete_slot(slot: DoctorAvailability) -> None:
    """Remove a slot - only when nobody has booked it."""
    if slot.booked_count:
        raise ValueError(
            f"This slot has {slot.booked_count} booked appointment(s) and cannot be "
            "removed. Cancel those appointments first."
        )
    db.session.delete(slot)
    db.session.commit()


def toggle_slot(slot: DoctorAvailability) -> bool:
    """Hide or show a slot. A slot with bookings cannot be hidden."""
    if slot.is_active and slot.booked_count:
        raise ValueError(
            f"This slot has {slot.booked_count} booked appointment(s), so it cannot be "
            "hidden. Cancel those appointments first."
        )
    slot.is_active = not slot.is_active
    db.session.commit()
    return slot.is_active


# ---------------------------------------------------------------------------
# Patient side
# ---------------------------------------------------------------------------
def bookable_doctors(
    name: str = "", specialization: str = "", department_id: int = 0
) -> list[Doctor]:
    """Doctors a patient may book with, filtered by name/specialization/department.

    Only doctors who are enabled, whose account is active and whose department
    is still active can appear - the same rule the booking service enforces.
    """
    query = (
        Doctor.query.join(Doctor.user)
        .join(Doctor.department)
        .filter(
            Doctor.is_available.is_(True),
            User.is_active.is_(True),
            User.role == Role.DOCTOR,
            Department.is_active.is_(True),
        )
    )

    if name:
        query = query.filter(User.full_name.ilike(f"%{name.strip()}%"))
    if specialization:
        query = query.filter(Doctor.specialization == specialization)
    if department_id:
        query = query.filter(Doctor.department_id == department_id)

    return query.order_by(Doctor.specialization, User.full_name).all()


def department_options() -> list[Department]:
    """Active departments for the patient search filters."""
    return Department.query.filter_by(is_active=True).order_by(Department.name).all()


def doctor_count_by_department() -> dict[int, int]:
    """Bookable doctors per department, shown on the department chips."""
    counts: dict[int, int] = {}
    for doctor in bookable_doctors():
        counts[doctor.department_id] = counts.get(doctor.department_id, 0) + 1
    return counts


def specialization_options() -> list[str]:
    """Distinct specializations among doctors a patient can book."""
    rows = (
        db.session.query(Doctor.specialization)
        .join(Doctor.user)
        .join(Doctor.department)
        .filter(
            Doctor.is_available.is_(True),
            User.is_active.is_(True),
            User.role == Role.DOCTOR,
            Department.is_active.is_(True),
        )
        .distinct()
        .order_by(Doctor.specialization)
        .all()
    )
    return [row[0] for row in rows]


def book_slot(patient: Patient, slot: DoctorAvailability, reason: str = "") -> Appointment:
    """Create a booked appointment for a published slot.

    The date and time come from the slot itself, never from the browser, so a
    patient cannot book a time the doctor never published.
    """
    if not slot.is_active:
        raise ValueError("This slot is no longer open for booking.")
    if _is_past(slot):
        raise ValueError("That slot has already passed. Please choose another time.")
    if not slot.doctor.is_bookable:
        raise ValueError("This doctor is not accepting bookings at the moment.")

    # "Don't book the same appointment twice": same patient, same slot, still
    # active. Checked before capacity so a patient who already holds the slot
    # gets the accurate message even when it is full.
    already = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.availability_id == slot.id,
        Appointment.status != AppointmentStatus.CANCELLED,
    ).first()
    if already is not None:
        raise ValueError(
            "You have already booked this slot. Choose a different time, or cancel "
            "the existing appointment first."
        )

    if slot.is_full:
        raise ValueError("This slot is fully booked. Please choose another time.")

    # Each booking inside a multi-patient slot gets its own start time, which
    # keeps the database's one-active-booking-per-moment index happy.
    step = max(_duration_minutes(slot.start_time, slot.end_time) // slot.max_patients, 1)
    start_dt = datetime.combine(slot.available_date, slot.start_time)
    appointment_time = (start_dt + timedelta(minutes=step * slot.booked_count)).time()

    appointment = Appointment(
        patient_id=patient.id,
        doctor_id=slot.doctor_id,
        availability=slot,
        appointment_date=slot.available_date,
        appointment_time=appointment_time,
        status=AppointmentStatus.BOOKED,
        reason=(reason or "").strip() or None,
    )
    try:
        db.session.add(appointment)
        # flush runs the INSERT inside this transaction, so the partial unique
        # indexes on the appointments table are checked *before* we commit.
        db.session.flush()
        db.session.commit()
    except IntegrityError:
        # Someone booked the same moment between our checks and the insert.
        db.session.rollback()
        raise ValueError("That time was just taken. Please choose another slot.")

    return appointment
