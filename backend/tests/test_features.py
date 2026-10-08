"""Heart-disease prediction, doctor schedules, lockout, password change, analytics."""
from datetime import date, timedelta

from conftest import PASSWORD
from test_api import DIABETES, new_patient, next_weekday

HEART = dict(age=63, sex=1, cp=0, trestbps=145, chol=233, fbs=1, restecg=0, thalach=150, exang=0, oldpeak=2.3,
             slope=0, ca=0, thal=1)


def first_doctor(client, headers):
    return client.get("/api/doctors", headers=headers).json()[0]["doctor_id"]


# ---- heart disease
def test_heart_prediction_and_validation(client, reception, doctor):
    p = new_patient(client, reception)
    pid = p["patient_id"]
    r = client.post("/api/predict/heart-disease", headers=doctor, json={"patient_id": pid, **HEART})
    assert r.status_code == 201, r.text
    out = r.json()
    assert out["disease_type"] == "heart_disease" and out["model_version"].startswith("heart-")
    assert {e["feature"] for e in out["explanation"]} == set(HEART)
    assert 0 <= out["risk_score"] <= 1

    # a clearly healthy profile scores lower than a clearly at-risk one
    healthy = {**HEART, "age": 35, "sex": 0, "cp": 2, "thalach": 185, "exang": 0, "oldpeak": 0.0, "slope": 2, "ca": 0, "thal": 2}
    risky = {**HEART, "age": 62, "sex": 1, "cp": 0, "thalach": 105, "exang": 1, "oldpeak": 3.5, "slope": 1, "ca": 3, "thal": 3}
    lo = client.post("/api/predict/heart-disease", headers=doctor, json={"patient_id": pid, **healthy}).json()
    hi = client.post("/api/predict/heart-disease", headers=doctor, json={"patient_id": pid, **risky}).json()
    assert hi["risk_score"] > lo["risk_score"]

    # history can be filtered by disease and diabetes/heart records don't mix
    client.post("/api/predict/diabetes", headers=doctor, json={"patient_id": pid, **DIABETES})
    heart_hist = client.get(f"/api/predictions/{pid}", headers=doctor, params={"disease": "heart_disease"}).json()
    assert len(heart_hist) == 3 and all(h["disease_type"] == "heart_disease" for h in heart_hist)
    assert len(client.get(f"/api/predictions/{pid}", headers=doctor).json()) == 4

    assert client.post("/api/predict/heart-disease", headers=doctor,
                       json={"patient_id": pid, **{**HEART, "cp": 9}}).status_code == 422
    assert client.post("/api/predict/heart-disease", headers=reception,
                       json={"patient_id": pid, **HEART}).status_code == 403


def test_models_registered_and_usage(client, analyst):
    models = client.get("/api/models", headers=analyst).json()
    assert {m["disease_type"] for m in models} == {"diabetes", "heart_disease"}
    assert all(m["metrics"]["comparison"] for m in models)
    usage = client.get("/api/models/usage", headers=analyst).json()
    assert usage and all(set(u["risk_levels"]) == {"low", "moderate", "high"} for u in usage)


def test_prediction_csv_export_is_deidentified(client, analyst, doctor, reception):
    p = new_patient(client, reception, "Csv Person")
    client.post("/api/predict/diabetes", headers=doctor, json={"patient_id": p["patient_id"], **DIABETES})
    r = client.get("/api/reports/predictions.csv", headers=analyst)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert r.text.splitlines()[0].startswith("prediction_id,patient_id,disease_type")
    assert "Csv Person" not in r.text
    assert client.get("/api/reports/predictions.csv", headers=doctor).status_code == 403


# ---- schedules
def test_slots_and_schedule_enforcement(client, admin, reception):
    p = new_patient(client, reception)
    doc = first_doctor(client, reception)
    day = next_weekday(14)
    slots = client.get(f"/api/doctors/{doc}/slots", headers=reception, params={"date": day.isoformat()}).json()
    assert "09:00" in slots["slots"] and "13:00" not in slots["slots"] and "12:30" in slots["slots"]
    assert "13:30" not in slots["slots"]  # lunch break

    saturday = day + timedelta(days=(5 - day.weekday()) % 7 or 7)
    assert client.get(f"/api/doctors/{doc}/slots", headers=reception, params={"date": saturday.isoformat()}).json()["slots"] == []

    body = {"patient_id": p["patient_id"], "doctor_id": doc, "date": day.isoformat(), "purpose": "x"}
    assert client.post("/api/appointments", headers=reception, json={**body, "time": "13:30:00"}).status_code == 422  # break
    assert client.post("/api/appointments", headers=reception, json={**body, "time": "09:10:00"}).status_code == 422  # off-grid
    assert client.post("/api/appointments", headers=reception,
                       json={**body, "date": saturday.isoformat(), "time": "09:00:00"}).status_code == 422  # weekend
    ok = client.post("/api/appointments", headers=reception, json={**body, "time": "09:30:00"})
    assert ok.status_code == 201, ok.text
    after = client.get(f"/api/doctors/{doc}/slots", headers=reception, params={"date": day.isoformat()}).json()["slots"]
    assert "09:30" not in after  # booked slot disappears

    # reschedule is also checked against the schedule
    aid = ok.json()["appointment_id"]
    assert client.patch(f"/api/appointments/{aid}", headers=reception, json={"time": "13:30:00"}).status_code == 422


def test_admin_sets_availability(client, admin, reception):
    d = client.post("/api/doctors", headers=admin, json={
        "name": "Dr. Schedule", "specialization": "Test", "department_id": client.get("/api/departments", headers=admin).json()[0]["department_id"]}).json()
    did = d["doctor_id"]
    assert client.get(f"/api/doctors/{did}/availability", headers=reception).json() == []
    day = next_weekday(20)
    bad = [{"weekday": 0, "start_time": "09:00:00", "end_time": "12:00:00"},
           {"weekday": 0, "start_time": "11:00:00", "end_time": "14:00:00"}]
    assert client.put(f"/api/doctors/{did}/availability", headers=admin, json=bad).status_code == 422
    assert client.put(f"/api/doctors/{did}/availability", headers=admin,
                      json=[{"weekday": 0, "start_time": "12:00:00", "end_time": "09:00:00"}]).status_code == 422
    good = [{"weekday": day.weekday(), "start_time": "10:00:00", "end_time": "11:00:00"}]
    assert client.put(f"/api/doctors/{did}/availability", headers=reception, json=good).status_code == 403
    assert client.put(f"/api/doctors/{did}/availability", headers=admin, json=good).status_code == 200
    slots = client.get(f"/api/doctors/{did}/slots", headers=reception, params={"date": day.isoformat()}).json()["slots"]
    assert slots == ["10:00", "10:30"]


# ---- lockout & password
def test_login_lockout_after_repeated_failures(client):
    email = "lockme@hospital.example.com"  # does not exist: lockout must still apply (no user enumeration)
    for _ in range(5):
        assert client.post("/api/auth/login", json={"email": email, "password": "nope"}).status_code == 401
    r = client.post("/api/auth/login", json={"email": email, "password": "nope"})
    assert r.status_code == 429 and "Try again" in r.json()["detail"]


def test_lockout_blocks_real_account_then_success_resets_counter(client):
    email = "reception@hospital.example.com"
    for _ in range(3):
        client.post("/api/auth/login", json={"email": email, "password": "wrong"})
    ok = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert ok.status_code == 200  # fewer than 5 failures -> still allowed, and the counter resets
    for _ in range(4):
        assert client.post("/api/auth/login", json={"email": email, "password": "wrong"}).status_code == 401


def test_change_password(client, admin):
    r = client.post("/api/users", headers=admin, json={"name": "Pw Tester", "email": "pw@hospital.example.com",
                                                       "password": "OldPassw0rd!", "role": "analyst"})
    assert r.status_code == 201
    tok = client.post("/api/auth/login", json={"email": "pw@hospital.example.com", "password": "OldPassw0rd!"}).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    assert client.post("/api/auth/change-password", headers=h,
                       json={"current_password": "bad", "new_password": "NewPassw0rd!"}).status_code == 400
    assert client.post("/api/auth/change-password", headers=h,
                       json={"current_password": "OldPassw0rd!", "new_password": "OldPassw0rd!"}).status_code == 422
    assert client.post("/api/auth/change-password", headers=h,
                       json={"current_password": "OldPassw0rd!", "new_password": "short"}).status_code == 422
    assert client.post("/api/auth/change-password", headers=h,
                       json={"current_password": "OldPassw0rd!", "new_password": "NewPassw0rd!"}).status_code == 204
    assert client.post("/api/auth/login", json={"email": "pw@hospital.example.com", "password": "OldPassw0rd!"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "pw@hospital.example.com", "password": "NewPassw0rd!"}).status_code == 200


# ---- analytics
def test_dashboard_analytics(client, doctor):
    d = client.get("/api/dashboard", headers=doctor).json()
    assert {"appointments_by_department", "predictions_by_disease", "predictions_last_14_days"} <= set(d)
    assert len(d["predictions_last_14_days"]) == 14
    assert set(d["predictions_by_disease"]) >= {"diabetes", "heart_disease"}
    assert sum(x["count"] for x in d["predictions_last_14_days"]) <= d["totals"]["predictions"]
    assert any(x["department"] == "Cardiology" for x in d["appointments_by_department"])
