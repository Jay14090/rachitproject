"""Demo data so a fresh clone has something to look at. Disable with SEED_DEMO_DATA=0."""
import random
from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from .models import Appointment, Department, Doctor, DoctorAvailability, Patient, User
from .security import hash_password

DEMO_PASSWORD = "Password123!"


def seed(db: Session) -> None:
    if db.query(User).count():
        return
    depts = [Department(department_name=n, description=d) for n, d in [
        ("General Medicine", "Primary care and internal medicine"),
        ("Cardiology", "Heart and vascular care"),
        ("Endocrinology", "Diabetes and hormonal disorders"),
        ("Pediatrics", "Child healthcare")]]
    db.add_all(depts)
    db.flush()
    doctors = [Doctor(name="Dr. Asha Verma", specialization="Internal Medicine", department_id=depts[0].department_id),
               Doctor(name="Dr. Rohan Mehta", specialization="Cardiologist", department_id=depts[1].department_id),
               Doctor(name="Dr. Neha Kapoor", specialization="Endocrinologist", department_id=depts[2].department_id)]
    db.add_all(doctors)
    db.flush()
    # Mon-Fri 09:00-13:00 and 14:00-17:00 for every demo doctor.
    for d in doctors:
        for wd in range(5):
            db.add_all([DoctorAvailability(doctor_id=d.doctor_id, weekday=wd, start_time=time(9), end_time=time(13)),
                        DoctorAvailability(doctor_id=d.doctor_id, weekday=wd, start_time=time(14), end_time=time(17))])
    pw = hash_password(DEMO_PASSWORD)
    db.add_all([
        User(name="System Admin", email="admin@hospital.example.com", password_hash=pw, role="admin"),
        User(name="Dr. Asha Verma", email="doctor@hospital.example.com", password_hash=pw, role="doctor",
             doctor_id=doctors[0].doctor_id),
        User(name="Riya Front-Desk", email="reception@hospital.example.com", password_hash=pw, role="reception"),
        User(name="Amit Analyst", email="analyst@hospital.example.com", password_hash=pw, role="analyst"),
    ])
    rng = random.Random(7)
    names = ["Rahul Sharma", "Priya Singh", "Amit Patel", "Sneha Reddy", "Vikram Joshi", "Anjali Nair",
             "Karan Malhotra", "Meera Iyer"]
    patients = [Patient(name=n, date_of_birth=date(rng.randint(1950, 2005), rng.randint(1, 12), rng.randint(1, 28)),
                        gender=rng.choice(["male", "female"]), contact=f"98{rng.randint(10000000, 99999999)}")
                for n in names]
    db.add_all(patients)
    db.flush()
    start = datetime.now().date() + timedelta(days=1)
    while start.weekday() >= 5:  # first weekday from tomorrow, to match the doctors' schedules
        start += timedelta(days=1)
    for i, p in enumerate(patients[:5]):
        day = start
        for _ in range(i % 3):
            day += timedelta(days=1)
            while day.weekday() >= 5:
                day += timedelta(days=1)
        db.add(Appointment(patient_id=p.patient_id, doctor_id=doctors[i % 3].doctor_id,
                           date=day, time=time(9 + i % 4, 0), purpose="Routine check-up"))
    db.commit()
