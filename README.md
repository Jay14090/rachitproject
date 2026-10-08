# Smart Hospital Management & Disease Risk Prediction System

Full-stack hospital app (React + FastAPI + SQL) with machine-learning **diabetes** and **heart-disease** risk
prediction. This repo is the **~70% milestone** of the project plan in
*Smart_Hospital_Advanced_Project_Document_Mid_November_2026.docx*: a working, tested system you can run today.

> Predictions are model-generated decision-support estimates. They are **not** medical diagnoses.

## Quick start

```bash
./run.sh            # creates venv, installs deps, trains models if needed, starts API + UI
```

Open <http://localhost:5173>. API docs (Swagger): <http://localhost:8000/docs>.

Demo logins (password `Password123!`): `admin@`, `doctor@`, `reception@`, `analyst@` + `hospital.example.com`.
Demo data is seeded on first start (disable with `SEED_DEMO_DATA=0`).

Manual setup:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
pip install -r ml/requirements.txt                  # only to retrain models (adds XGBoost to the comparison)
python ml/train_diabetes.py && python ml/train_heart.py   # optional: artifacts are already committed
(cd backend && uvicorn app.main:app --port 8000)    # API
(cd frontend && npm install && npm run dev)         # UI (proxies /api -> :8000)
(cd backend && python -m pytest)                    # 23 API / RBAC / ML / performance tests
(cd frontend && npm test)                           # 9 UI tests
```

If the API logs a scikit-learn version warning (or fails to load a model), re-run the two training scripts.

### Database: SQLite (default) or MySQL

SQLite needs no setup. For MySQL: `docker compose up -d db`, then

```bash
export DATABASE_URL="mysql+pymysql://hospital:hospital@127.0.0.1:3306/smart_hospital"
```

Tables are created on start. There are no migrations yet, so after pulling a version that adds columns to an
existing table you must recreate the DB (new tables are added automatically).

### Docker (full stack)

`docker compose up --build` → UI on <http://localhost:8080>, API on :8000 (MySQL included). Set `SECRET_KEY` first.

> **Not verified:** the Docker images and the MySQL path are written and the compose file validates, but there was
> no Docker daemon or MySQL server where this was built, so neither has actually been run. Expect to debug a
> little on first use. SQLite + `./run.sh` is the tested path.

Environment variables: `DATABASE_URL`, `SECRET_KEY` (**set this outside dev**), `ACCESS_TOKEN_MINUTES`,
`CORS_ORIGINS`, `ML_ARTIFACT_DIR`, `SEED_DEMO_DATA`.

## What's implemented vs. the plan

| Doc area | Status |
|---|---|
| Login, JWT, role-based access (admin / doctor / reception / analyst), change password | ✅ |
| Login lockout (5 failures → 15 min), no user enumeration | ✅ |
| Patients: register, search, view, update | ✅ |
| Doctors & departments; **weekly doctor schedules**, free-slot picker, schedule-aware booking | ✅ |
| Appointments: create, reschedule, cancel, complete; double-booking, past-date and off-schedule protection | ✅ |
| Medical records (measurements, symptoms, notes) | ✅ |
| **Diabetes** and **heart-disease** risk prediction; LR / Decision Tree / Random Forest / XGBoost compared | ✅ |
| Model versions, prediction history, risk-over-time chart, per-prediction explanation | ✅ (perturbation-based, not SHAP) |
| Model usage monitoring page, de-identified CSV export | ✅ |
| Dashboard: counts, 7-day appointments, by department, predictions by disease / over time, risk mix | ✅ |
| Audit logging (IDs only, no PHI), input validation, safe error responses | ✅ |
| Backend tests (API, RBAC, validation, ML flows, performance), UI tests, GitHub Actions CI | ✅ |
| Architecture, ER diagram, API reference, testing report (`docs/`) | ✅ |
| Dockerfiles + compose with MySQL | ⚠️ written, not run |
| SHAP explanations, EDA notebooks, automated retraining | ⏳ |
| Doctor-scoped patient access (doctors currently see all patients) | ⏳ |
| Email/SMS reminders, HTTPS/reverse-proxy hardening, cloud deployment | ⏳ |
| DB migrations (Alembic), refresh tokens / token revocation | ⏳ |
| Browser end-to-end tests in CI, load testing, security review, final PPT / report | ⏳ |

## Layout

```
backend/   FastAPI app (app/routers/*), SQLAlchemy models, tests/
frontend/  React + Vite + Recharts UI (src/pages/*), Vitest tests
ml/        train_diabetes.py, train_heart.py, shared common.py, public datasets, versioned model artifacts
docs/      ARCHITECTURE.md (diagrams + decisions), API.md, TESTING.md
```

## Role matrix

| | admin | doctor | reception | analyst |
|---|:-:|:-:|:-:|:-:|
| Users, audit log | ✅ | | | |
| Doctors / departments / schedules: edit | ✅ | | | |
| Patients: read | ✅ | ✅ | ✅ | |
| Patients: register / edit | ✅ | | ✅ | |
| Appointments | ✅ | ✅ | ✅ | |
| Medical records, predictions | ✅ | ✅ | | |
| Dashboard (aggregates only) | ✅ | ✅ | ✅ | ✅ |
| Model metrics & usage | ✅ | ✅ | | ✅ |
| Prediction CSV export (patient IDs only) | ✅ | | | ✅ |

## Notes on the ML module

* **Data:** Pima Indians Diabetes (n=768) and Cleveland Heart Disease (n=303), both public and de-identified.
  They are small and from specific populations — treat results as a demonstration of the pipeline, not clinical
  performance.
* **Heart label:** the CSV mirror used stores `target=1` for *healthy* patients (verified from the feature
  distributions), so the training script defines disease = 1 − target and treats the invalid codes `thal=0` and
  `ca=4` as missing. Categorical inputs (chest-pain type, ECG, slope, thalassemia) use the dataset's own numeric
  codes, which the UI shows as "Code N".
* **Selection:** the model is chosen by 5-fold cross-validated ROC-AUC on the training split; reported metrics come
  from a separate 20% test split. Current results are in `docs/TESTING.md` and on the **ML Models** page.
* **Explanations:** each feature is swapped for the training median and the change in predicted risk is shown.
