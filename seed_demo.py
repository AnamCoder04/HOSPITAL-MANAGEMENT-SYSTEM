"""Demo data for MediCare HMS.

Creates two doctors, two patients, published availability slots, a completed
visit with a treatment record, an upcoming booking and a cancelled booking.

    python seed_demo.py

Safe to run more than once: records are looked up by their natural keys
(e-mail address, doctor + date + time) and only missing ones are created.

Demo logins created by this script
----------------------------------
Doctor   ananya.sharma@medicare-demo.com   Doctor@123
Doctor   vikram.rao@medicare-demo.com      Doctor@123
Patient  rohit.verma@example.com           Patient@123
Patient  meera.iyer@example.com            Patient@123
"""

from __future__ import annotations

from datetime import date, time, timedelta

from app.extensions import db
from app.models import (
    Appointment,
    AppointmentStatus,
    Department,
    Doctor,
    DoctorAvailability,
    Patient,
    Role,
    Treatment,
    User,
)

DOCTOR_PASSWORD = "Doctor@123"
PATIENT_PASSWORD = "Patient@123"


def _get_or_create_user(email: str, full_name: str, phone: str, role: str, password: str) -> User:
    user = User.query.filter_by(email=email).first()
    if user is not None:
        return user

    user = User(full_name=full_name, email=email, phone=phone, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    return user


def _get_or_create_doctor(
    email: str, full_name: str, phone: str, department_name: str, **profile
) -> Doctor:
    user = _get_or_create_user(email, full_name, phone, Role.DOCTOR, DOCTOR_PASSWORD)
    doctor = user.doctor
    if doctor is not None:
        return doctor

    department = Department.query.filter_by(name=department_name).first()
    if department is None:
        department = Department(name=department_name, description=f"{department_name} department.")
        db.session.add(department)
        db.session.flush()

    doctor = Doctor(user_id=user.id, department_id=department.id, **profile)
    db.session.add(doctor)
    db.session.flush()
    return doctor


def _get_or_create_patient(email: str, full_name: str, phone: str, **profile) -> Patient:
    user = _get_or_create_user(email, full_name, phone, Role.PATIENT, PATIENT_PASSWORD)
    patient = user.patient
    if patient is not None:
        return patient

    patient = Patient(user_id=user.id, **profile)
    db.session.add(patient)
    db.session.flush()
    return patient


def _get_or_create_slot(doctor: Doctor, day: date, start: time, end: time, capacity: int = 1) -> DoctorAvailability:
    slot = DoctorAvailability.query.filter_by(
        doctor_id=doctor.id, available_date=day, start_time=start
    ).first()
    if slot is not None:
        return slot

    slot = DoctorAvailability(
        doctor_id=doctor.id,
        available_date=day,
        start_time=start,
        end_time=end,
        max_patients=capacity,
        is_active=True,
    )
    db.session.add(slot)
    db.session.flush()
    return slot


def _get_or_create_appointment(
    patient: Patient, doctor: Doctor, day: date, at: time, status: str, **fields
) -> Appointment:
    appointment = Appointment.query.filter_by(
        patient_id=patient.id,
        doctor_id=doctor.id,
        appointment_date=day,
        appointment_time=at,
    ).first()
    if appointment is not None:
        return appointment

    appointment = Appointment(
        patient_id=patient.id,
        doctor_id=doctor.id,
        appointment_date=day,
        appointment_time=at,
        status=status,
        **fields,
    )
    db.session.add(appointment)
    db.session.flush()
    return appointment


def seed(app=None, quiet: bool = False) -> None:
    if app is None:
        from app import create_app

        app = create_app()

    with app.app_context():
        today = date.today()
        tomorrow = today + timedelta(days=1)

        # --- Doctors -----------------------------------------------------
        ananya = _get_or_create_doctor(
            "ananya.sharma@medicare-demo.com",
            "Ananya Sharma",
            "9810001001",
            "Cardiology",
            specialization="Cardiology",
            qualifications="MBBS, MD (Cardiology)",
            license_no="MCI-DEMO-1001",
            experience_years=12,
            consultation_fee=900,
            room_no="204",
            bio="Interventional cardiologist with a focus on preventive heart care.",
            is_available=True,
        )
        vikram = _get_or_create_doctor(
            "vikram.rao@medicare-demo.com",
            "Vikram Rao",
            "9810001002",
            "Neurology",
            specialization="Neurology",
            qualifications="MBBS, DM (Neurology)",
            license_no="MCI-DEMO-1002",
            experience_years=9,
            consultation_fee=800,
            room_no="311",
            bio="Treats migraine, epilepsy and movement disorders.",
            is_available=True,
        )

        # --- Patients ----------------------------------------------------
        rohit = _get_or_create_patient(
            "rohit.verma@example.com", "Rohit Verma", "9820002001",
            date_of_birth=date(1991, 4, 18), gender="Male", blood_group="B+",
            address="12 Rose Villa, Pune", emergency_contact="9820002099",
            allergies="Penicillin",
        )
        meera = _get_or_create_patient(
            "meera.iyer@example.com", "Meera Iyer", "9820002002",
            date_of_birth=date(1987, 11, 2), gender="Female", blood_group="O+",
            address="8 Lake Road, Pune", emergency_contact="9820002098",
        )

        # --- Availability (tomorrow and the day after) -------------------
        slot_0900 = _get_or_create_slot(ananya, tomorrow, time(9, 0), time(9, 30))
        slot_1000 = _get_or_create_slot(ananya, tomorrow, time(10, 0), time(10, 30))
        slot_1100 = _get_or_create_slot(vikram, tomorrow, time(11, 0), time(11, 30))
        _get_or_create_slot(ananya, tomorrow + timedelta(days=1), time(9, 0), time(9, 30))

        # --- Completed visit with a treatment record ---------------------
        past_day = today - timedelta(days=7)
        past = _get_or_create_appointment(
            rohit, ananya, past_day, time(9, 0), AppointmentStatus.COMPLETED,
            reason="Chest tightness while walking",
        )
        if past.treatment is None:
            db.session.add(
                Treatment(
                    appointment_id=past.id,
                    doctor_id=ananya.id,
                    diagnosis="Stable angina, suspected",
                    prescription="Aspirin 75 mg once daily\nAtorvastatin 20 mg at night",
                    treatment_plan="ECG and lipid profile, cardiology review in two weeks",
                    notes="BP 128/82. Advised low-salt diet and 30 minutes of walking daily.",
                    follow_up_date=today + timedelta(days=7),
                )
            )

        # --- Upcoming bookings -------------------------------------------
        _get_or_create_appointment(
            rohit, ananya, tomorrow, time(9, 0), AppointmentStatus.BOOKED,
            availability_id=slot_0900.id, reason="Follow-up for chest tightness",
        )
        _get_or_create_appointment(
            meera, vikram, tomorrow, time(11, 0), AppointmentStatus.BOOKED,
            availability_id=slot_1100.id, reason="Recurring migraine",
        )

        # --- A cancelled booking, to show released slots -----------------
        _get_or_create_appointment(
            meera, ananya, today - timedelta(days=1), time(10, 0), AppointmentStatus.CANCELLED,
            cancel_reason="Cancelled by the patient.",
        )

        db.session.commit()

        if not quiet:
            print("Demo data ready.")
            print(f"  Doctors : {Doctor.query.count()}   Patients: {Patient.query.count()}   "
                  f"Appointments: {Appointment.query.count()}   Treatments: {Treatment.query.count()}")
            print("  Doctor  : ananya.sharma@medicare-demo.com / Doctor@123")
            print("  Doctor  : vikram.rao@medicare-demo.com    / Doctor@123")
            print("  Patient : rohit.verma@example.com         / Patient@123")
            print("  Patient : meera.iyer@example.com          / Patient@123")
            print(f"  Open slots: {slot_1000.label} tomorrow with Dr. Ananya Sharma")


if __name__ == "__main__":
    seed()
