"""Database models.

Task 3 fills this package with the seven SQLAlchemy models:

    user.py          -> User
    department.py    -> Department
    doctor.py        -> Doctor
    patient.py       -> Patient
    availability.py  -> DoctorAvailability
    appointment.py   -> Appointment
    treatment.py     -> Treatment

Every model must be imported in this file so that db.create_all() can see
all of them before it builds the tables (SQLAlchemy only creates metadata
for models that have actually been imported).
"""
