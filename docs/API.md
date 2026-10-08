# API reference

Interactive docs (with request/response schemas): `http://localhost:8000/docs`.
All routes except `/api/auth/login` and `/api/health` need `Authorization: Bearer <token>`.
Validation failures return `422 {"detail": "Validation failed", "errors": [{"field", "message"}]}`.

| Method | Endpoint | Roles | Purpose |
|---|---|---|---|
| POST | `/api/auth/login` | public | Authenticate (5 failures → 15-minute lockout, HTTP 429) |
| GET | `/api/auth/me` | any | Current user |
| POST | `/api/auth/change-password` | any | Change own password |
| GET, POST | `/api/users` | admin | List / create users |
| PATCH | `/api/users/{id}` | admin | Update role, status, password |
| GET, POST | `/api/departments` | any / admin | List / create |
| PUT, DELETE | `/api/departments/{id}` | admin | Rename / delete (blocked while doctors are assigned) |
| GET, POST | `/api/doctors` | any / admin | List (filter `department_id`, `active_only`) / create |
| PATCH | `/api/doctors/{id}` | admin | Update |
| GET, PUT | `/api/doctors/{id}/availability` | any / admin | Weekly working windows (PUT replaces them; empty list = no restriction) |
| GET | `/api/doctors/{id}/slots?date=` | any | Free 30-minute slots on a date |
| GET, POST | `/api/patients` | admin, doctor, reception / admin, reception | Search (`q`, `skip`, `limit`) / register |
| GET, PATCH | `/api/patients/{id}` | read: admin, doctor, reception / write: admin, reception | View / update |
| GET, POST | `/api/appointments` | admin, doctor, reception | List (filters) / create |
| PATCH | `/api/appointments/{id}` | admin, doctor, reception | Reschedule or set status (`completed`, `cancelled`) |
| POST | `/api/medical-records` | admin, doctor | Create record |
| GET | `/api/medical-records/patient/{id}` | admin, doctor | Patient's records |
| POST | `/api/predict/diabetes` | admin, doctor | Diabetes risk estimate |
| POST | `/api/predict/heart-disease` | admin, doctor | Heart-disease risk estimate |
| GET | `/api/predictions/{patient_id}` | admin, doctor | History (optional `disease`) |
| GET | `/api/models` | admin, doctor, analyst | Model versions + evaluation metrics |
| GET | `/api/models/usage` | admin, doctor, analyst | Per-version usage and risk-level mix |
| GET | `/api/reports/predictions.csv` | admin, analyst | De-identified prediction export |
| GET | `/api/dashboard` | any | Aggregate statistics |
| GET | `/api/audit-logs` | admin | Audit trail (filters `action`, `user_id`) |
| GET | `/api/health` | public | Liveness |

### Prediction request / response (diabetes example)

```http
POST /api/predict/diabetes
{"patient_id": 3, "pregnancies": 2, "glucose": 148, "blood_pressure": 72, "skin_thickness": 35,
 "insulin": 0, "bmi": 33.6, "diabetes_pedigree": 0.627, "age": 50}

201 {"prediction_id": 12, "risk_score": 0.7421, "risk_level": "high", "result": "higher risk",
     "model_version": "diabetes-logistic-regression-v1",
     "explanation": [{"feature": "glucose", "value": 148.0, "impact": 0.2104}, ...],
     "disclaimer": "Model-generated risk estimate for decision support only. It is not a medical diagnosis."}
```

Risk levels: `low` < 0.33 ≤ `moderate` < 0.66 ≤ `high`. `impact` is the change in predicted probability versus
replacing that feature with the training median (positive = raises risk).
