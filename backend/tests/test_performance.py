"""Basic performance checks (doc section 16) at project scale: ~1000 patients.

Thresholds are deliberately generous (p95 over repeated calls) so they catch accidental N+1 queries or
full-table scans without being flaky on slow CI machines.
"""
import datetime as dt
import time
from datetime import date, timedelta

import pytest

from app.database import SessionLocal
from app.models import Appointment, Doctor, Patient
from test_api import DIABETES

P95_LIMIT_SECONDS = 1.0


@pytest.fixture(scope="module")
def big_dataset(client):
    with SessionLocal() as db:
        db.add_all(Patient(name=f"Perf Patient {i:04d}", date_of_birth=date(1970 + i % 30, 1 + i % 12, 1 + i % 28),
                           gender="female" if i % 2 else "male", contact=f"90000{i:05d}") for i in range(1000))
        db.commit()
        doc = db.query(Doctor).first().doctor_id
        pids = [p.patient_id for p in db.query(Patient).limit(300).all()]
        base = date.today() + timedelta(days=60)
        db.add_all(Appointment(patient_id=pid, doctor_id=doc, date=base + timedelta(days=i // 20),
                               time=dt.time(8 + (i % 20) // 2, 30 * (i % 2)), slot_key=None)
                   for i, pid in enumerate(pids))
        db.commit()


def p95(fn, n=15):
    times = []
    for _ in range(n):
        t = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t)
    times.sort()
    return times[int(0.95 * (len(times) - 1))]


def test_list_and_search_patients(client, reception, big_dataset):
    assert p95(lambda: client.get("/api/patients", headers=reception, params={"limit": 200})) < P95_LIMIT_SECONDS
    assert p95(lambda: client.get("/api/patients", headers=reception, params={"q": "Perf Patient 05"})) < P95_LIMIT_SECONDS


def test_dashboard_and_appointments(client, reception, big_dataset):
    assert p95(lambda: client.get("/api/dashboard", headers=reception)) < P95_LIMIT_SECONDS
    assert p95(lambda: client.get("/api/appointments", headers=reception, params={"limit": 500})) < P95_LIMIT_SECONDS


def test_prediction_latency(client, doctor, reception, big_dataset):
    pid = client.get("/api/patients", headers=reception, params={"limit": 1}).json()[0]["patient_id"]
    assert p95(lambda: client.post("/api/predict/diabetes", headers=doctor, json={"patient_id": pid, **DIABETES})) < P95_LIMIT_SECONDS
