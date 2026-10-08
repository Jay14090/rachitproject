# Smart Hospital Management & Disease Risk Prediction System

Full-stack hospital app (React + FastAPI + SQL) with a machine-learning diabetes-risk module.
This repo is the **~40% milestone** of the project plan in
*Smart_Hospital_Advanced_Project_Document_Mid_November_2026.docx*: a working, tested core you can run today
and keep building on.

> Predictions are model-generated decision-support estimates. They are **not** medical diagnoses.

## Quick start

```bash
./run.sh            # creates venv, installs deps, trains model if needed, starts API + UI
```

Open <http://localhost:5173>. API docs (Swagger): <http://localhost:8000/docs>.

Demo logins (password `Password123!`): `admin@`, `doctor@`, `reception@`, `analyst@` + `hospital.example.com`.
Demo data is seeded on first start (disable with `SEED_DEMO_DATA=0`).

Manual setup:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
python ml/train_diabetes.py                         # optional: artifacts are already committed
(cd backend && uvicorn app.main:app --port 8000)    # API
(cd frontend && npm install && npm run dev)         # UI (proxies /api -> :8000)
cd backend && python -m pytest                      # 11 API / RBAC / ML tests
```

### Using MySQL (as in the project doc)

SQLite is the zero-setup default. To use MySQL: `docker compose up -d db`, then

```bash
export DATABASE_URL="mysql+pymysql://hospital:hospital@127.0.0.1:3306/smart_hospital"
```

Tables are created automatically on start. *(The MySQL path is configured but was not exercised when this
was built; only SQLite was tested.)*

Other settings (env vars): `SECRET_KEY` (**set this outside dev**), `ACCESS_TOKEN_MINUTES`, `CORS_ORIGINS`, `ML_ARTIFACT_DIR`.

## What's implemented vs. the plan

| Doc area | Status |
|---|---|
| Login, JWT, role-based access (admin / doctor / reception / analyst) | ✅ |
| Patients: register, search, view, update | ✅ |
| Doctors & departments (admin-managed) | ✅ |
| Appointments: create, reschedule, cancel, complete; double-booking and past-date protection | ✅ |
| Medical records (measurements, symptoms, notes) | ✅ |
| **Diabetes** risk prediction: Logistic Regression / Decision Tree / Random Forest compared (CV + hold-out metrics) | ✅ |
| Model versions table, prediction history, risk level, per-prediction explanation | ✅ (perturbation-based, not SHAP) |
| Dashboard (counts, 7-day appointments, risk distribution), model metrics page | ✅ |
| Audit logging (IDs only, no PHI), input validation, safe error responses | ✅ |
| Automated tests (API, RBAC, validation, prediction flow) + GitHub Actions CI | ✅ |
| **Heart-disease** model + endpoint (`/api/predict/heart-disease`) | ⏳ next |
| XGBoost, SHAP, EDA notebooks, model monitoring | ⏳ |
| Doctor availability schedules, doctor-scoped patient access | ⏳ |
| Login rate-limiting / lockout, HTTPS, Docker packaging of the app, cloud deploy | ⏳ |
| Front-end tests, performance tests, final docs / PPT | ⏳ |

## Layout

```
backend/   FastAPI app (app/routers/*), SQLAlchemy models, tests/
frontend/  React + Vite + Recharts UI (src/pages/*)
ml/        train_diabetes.py, public Pima dataset, versioned model artifacts
```

## Role matrix

| | admin | doctor | reception | analyst |
|---|:-:|:-:|:-:|:-:|
| Users, audit log | ✅ | | | |
| Doctors / departments: edit | ✅ | | | |
| Patients: read | ✅ | ✅ | ✅ | |
| Patients: register / edit | ✅ | | ✅ | |
| Appointments | ✅ | ✅ | ✅ | |
| Medical records, predictions | ✅ | ✅ | | |
| Dashboard (aggregates only) | ✅ | ✅ | ✅ | ✅ |
| Model metrics | ✅ | ✅ | | ✅ |

## Notes on the ML module

* Data: public Pima Indians Diabetes dataset (n=768, 8 features). It is small and from a specific population, so
  treat results as a demonstration of the pipeline, not clinical performance. Retrain with `python ml/train_diabetes.py`.
* The model is chosen by 5-fold cross-validated ROC-AUC on the training split; reported metrics come from a separate 20% test split.
* Explanations: each feature is swapped for the training median and the change in predicted risk is shown.
