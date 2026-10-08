from datetime import date, timedelta

DIABETES = dict(pregnancies=2, glucose=148, blood_pressure=72, skin_thickness=35, insulin=0, bmi=33.6,
                diabetes_pedigree=0.627, age=50)


def new_patient(client, headers, name="Test Patient"):
    r = client.post("/api/patients", headers=headers, json={
        "name": name, "date_of_birth": "1990-05-17", "gender": "female", "contact": "9876543210"})
    assert r.status_code == 201, r.text
    return r.json()


# ---- auth
def test_login_rejects_bad_credentials(client):
    r = client.post("/api/auth/login", json={"email": "admin@hospital.example.com", "password": "wrong"})
    assert r.status_code == 401
    r = client.post("/api/auth/login", json={"email": "nobody@hospital.example.com", "password": "x"})
    assert r.status_code == 401


def test_protected_routes_need_token(client):
    assert client.get("/api/patients").status_code == 401
    assert client.get("/api/patients", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_me(client, doctor):
    r = client.get("/api/auth/me", headers=doctor)
    assert r.json()["role"] == "doctor"
    assert "password" not in r.text


# ---- RBAC
def test_rbac_matrix(client, admin, doctor, reception, analyst):
    assert client.get("/api/users", headers=admin).status_code == 200
    assert client.get("/api/users", headers=doctor).status_code == 403
    assert client.get("/api/audit-logs", headers=reception).status_code == 403
    assert client.get("/api/patients", headers=analyst).status_code == 403  # analysts get no PHI
    assert client.get("/api/patients", headers=doctor).status_code == 200
    assert client.get("/api/models", headers=analyst).status_code == 200
    assert client.post("/api/departments", headers=reception, json={"department_name": "X-Ray"}).status_code == 403
    p = new_patient(client, reception)
    # reception cannot read clinical data or run predictions
    assert client.get(f"/api/medical-records/patient/{p['patient_id']}", headers=reception).status_code == 403
    r = client.post("/api/predict/diabetes", headers=reception, json={"patient_id": p["patient_id"], **DIABETES})
    assert r.status_code == 403
    # doctors cannot register patients
    r = client.post("/api/patients", headers=doctor, json={
        "name": "Nope Nope", "date_of_birth": "1990-01-01", "gender": "male", "contact": "12345678"})
    assert r.status_code == 403


# ---- patients
def test_patient_crud_search_and_validation(client, reception):
    p = new_patient(client, reception, "Zelda Searchable")
    assert p["age"] >= 30
    r = client.get("/api/patients", headers=reception, params={"q": "searchable"})
    assert [x["patient_id"] for x in r.json()] == [p["patient_id"]]
    r = client.patch(f"/api/patients/{p['patient_id']}", headers=reception, json={"contact": "1112223333"})
    assert r.json()["contact"] == "1112223333"
    assert client.get("/api/patients/99999", headers=reception).status_code == 404
    bad = client.post("/api/patients", headers=reception, json={
        "name": "A", "date_of_birth": "2999-01-01", "gender": "x", "contact": "abc"})
    assert bad.status_code == 422
    assert "errors" in bad.json()
    assert "2999" not in bad.text  # submitted values are not echoed back


# ---- doctors / departments
def test_admin_manages_departments_and_doctors(client, admin):
    d = client.post("/api/departments", headers=admin, json={"department_name": "Neurology"})
    assert d.status_code == 201
    assert client.post("/api/departments", headers=admin, json={"department_name": "Neurology"}).status_code == 409
    doc = client.post("/api/doctors", headers=admin, json={
        "name": "Dr. New", "specialization": "Neurologist", "department_id": d.json()["department_id"]})
    assert doc.status_code == 201
    assert doc.json()["department"]["department_name"] == "Neurology"
    # cannot delete a department that still has doctors
    assert client.delete(f"/api/departments/{d.json()['department_id']}", headers=admin).status_code == 409
    assert client.post("/api/doctors", headers=admin, json={
        "name": "Dr. Bad", "specialization": "X Y", "department_id": 99999}).status_code == 422


# ---- appointments
def test_appointment_lifecycle_and_double_booking(client, reception):
    p = new_patient(client, reception)
    doc_id = client.get("/api/doctors", headers=reception).json()[0]["doctor_id"]
    day = (date.today() + timedelta(days=10)).isoformat()
    body = {"patient_id": p["patient_id"], "doctor_id": doc_id, "date": day, "time": "10:30:00", "purpose": "Checkup"}
    a = client.post("/api/appointments", headers=reception, json=body)
    assert a.status_code == 201, a.text
    aid = a.json()["appointment_id"]
    assert client.post("/api/appointments", headers=reception, json=body).status_code == 409  # same slot

    # reschedule to a free slot, then the old slot is bookable again
    r = client.patch(f"/api/appointments/{aid}", headers=reception, json={"time": "11:30:00"})
    assert r.status_code == 200 and r.json()["time"] == "11:30:00"
    assert client.post("/api/appointments", headers=reception, json=body).status_code == 201

    # cancel, then it can't be changed again
    assert client.patch(f"/api/appointments/{aid}", headers=reception, json={"status": "cancelled"}).json()["status"] == "cancelled"
    assert client.patch(f"/api/appointments/{aid}", headers=reception, json={"status": "completed"}).status_code == 409

    past = {**body, "date": (date.today() - timedelta(days=1)).isoformat()}
    assert client.post("/api/appointments", headers=reception, json=past).status_code == 422


# ---- medical records
def test_medical_record_flow(client, reception, doctor):
    p = new_patient(client, reception)
    r = client.post("/api/medical-records", headers=doctor, json={
        "patient_id": p["patient_id"], "measurements": {"bp_systolic": 128, "weight_kg": 71.5},
        "symptoms": "Fatigue", "notes": "Follow up in 2 weeks"})
    assert r.status_code == 201, r.text
    assert r.json()["doctor_name"] == "Dr. Asha Verma"  # taken from the logged-in doctor's profile
    assert client.post("/api/medical-records", headers=doctor, json={"patient_id": p["patient_id"]}).status_code == 422
    rows = client.get(f"/api/medical-records/patient/{p['patient_id']}", headers=doctor).json()
    assert len(rows) == 1


# ---- prediction
def test_diabetes_prediction_end_to_end(client, reception, doctor, admin):
    p = new_patient(client, reception)
    r = client.post("/api/predict/diabetes", headers=doctor, json={"patient_id": p["patient_id"], **DIABETES})
    assert r.status_code == 201, r.text
    out = r.json()
    assert 0 <= out["risk_score"] <= 1
    assert out["risk_level"] in {"low", "moderate", "high"}
    assert out["model_version"].startswith("diabetes-")
    assert len(out["explanation"]) == 8 and "not a medical diagnosis" in out["disclaimer"]

    # a clearly high-risk profile scores higher than a clearly low-risk one
    low = client.post("/api/predict/diabetes", headers=doctor, json={
        "patient_id": p["patient_id"], **{**DIABETES, "glucose": 85, "bmi": 22, "age": 25, "pregnancies": 0,
                                          "diabetes_pedigree": 0.2}}).json()
    high = client.post("/api/predict/diabetes", headers=doctor, json={
        "patient_id": p["patient_id"], **{**DIABETES, "glucose": 190, "bmi": 40, "age": 55}}).json()
    assert high["risk_score"] > low["risk_score"]

    hist = client.get(f"/api/predictions/{p['patient_id']}", headers=doctor).json()
    assert len(hist) == 3 and hist[0]["inputs"]["glucose"] == 190

    # input validation
    bad = client.post("/api/predict/diabetes", headers=doctor, json={"patient_id": p["patient_id"], **{**DIABETES, "glucose": 5000}})
    assert bad.status_code == 422
    assert client.post("/api/predict/diabetes", headers=doctor, json={"patient_id": 99999, **DIABETES}).status_code == 422

    models = client.get("/api/models", headers=admin).json()
    assert models[0]["active_flag"] and "roc_auc" in models[0]["metrics"]


# ---- audit + dashboard
def test_audit_trail_and_dashboard(client, admin, reception):
    p = new_patient(client, reception, "Audit Subject")
    logs = client.get("/api/audit-logs", headers=admin, params={"action": "patient_created"}).json()
    assert any(l["entity_id"] == str(p["patient_id"]) and l["user_name"] == "Riya Front-Desk" for l in logs)
    assert "Audit Subject" not in str(logs)  # no PHI in the audit log
    client.post("/api/auth/login", json={"email": "admin@hospital.example.com", "password": "bad"})
    assert client.get("/api/audit-logs", headers=admin, params={"action": "login_failed"}).json()

    d = client.get("/api/dashboard", headers=reception).json()
    assert d["totals"]["patients"] >= 1
    assert len(d["appointments_next_7_days"]) == 7
    assert set(d["risk_distribution"]) == {"low", "moderate", "high"}


def test_user_admin_safeguards(client, admin):
    me = client.get("/api/auth/me", headers=admin).json()
    assert client.patch(f"/api/users/{me['user_id']}", headers=admin, json={"status": "inactive"}).status_code == 400
    r = client.post("/api/users", headers=admin, json={"name": "New Staff", "email": "New@Hospital.example.com",
                                                       "password": "LongEnough1!", "role": "reception"})
    assert r.status_code == 201 and r.json()["email"] == "new@hospital.example.com"
    assert client.post("/api/users", headers=admin, json={"name": "Dup", "email": "new@hospital.example.com",
                                                          "password": "LongEnough1!", "role": "reception"}).status_code == 409
    # deactivated user can no longer log in
    uid = r.json()["user_id"]
    client.patch(f"/api/users/{uid}", headers=admin, json={"status": "inactive"})
    assert client.post("/api/auth/login", json={"email": "new@hospital.example.com", "password": "LongEnough1!"}).status_code == 401
