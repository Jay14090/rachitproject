# Testing & evaluation

Run everything:

```bash
cd backend && python -m pytest          # 23 tests
cd frontend && npm test                 # 9 tests (Vitest + Testing Library)
```

CI (`.github/workflows/ci.yml`) runs both plus the production build on every push.

| Plan item (doc §16) | Where |
|---|---|
| Functional: login, patients, doctors, appointments, records | `backend/tests/test_api.py` |
| Database CRUD & relationships (e.g. department with doctors can't be deleted, slot re-booking after cancel) | `test_api.py`, `test_features.py` |
| API request/response, validation, no echo of submitted values | `test_api.py::test_patient_crud_search_and_validation` |
| Role-based access matrix | `test_api.py::test_rbac_matrix` |
| Authentication hardening: lockout, no user enumeration, password change | `test_features.py` |
| Doctor schedules and slot booking rules | `test_features.py::test_slots_and_schedule_enforcement`, `test_admin_sets_availability` |
| ML end-to-end: input → prediction → stored history; high-risk profile scores above low-risk profile (both diseases) | `test_api.py`, `test_features.py` |
| Audit-log verification, no PHI in logs | `test_api.py::test_audit_trail_and_dashboard` |
| Basic performance (p95 < 1 s on ~1000 patients, ~300 appointments) | `test_performance.py` |
| Front-end: API client, role-based navigation, login errors, prediction form → endpoint | `frontend/src/__tests__/` |

## Model evaluation (held-out 20 % test split; selection by 5-fold CV ROC-AUC)

| Disease | Selected | Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---|---|---|---|---|---|
| Diabetes (Pima, n=768) | Logistic Regression | 0.734 | 0.603 | 0.704 | 0.650 | 0.813 |
| Heart disease (Cleveland, n=303) | Random Forest | 0.820 | 0.840 | 0.750 | 0.793 | 0.918 |

The full per-algorithm comparison (including confusion matrices) is on the **ML Models** page and in
`ml/artifacts/*_meta.json`. Both datasets are small; with 61 (heart) and 154 (diabetes) test rows, a single
patient changes accuracy by about 0.7 points (diabetes) or 1.6 points (heart), so treat these as demonstration figures, not clinical validation.

## Not covered yet

* No browser end-to-end test in CI (the flows were exercised manually with Playwright during development).
* Docker images and the MySQL path are configured but have not been built/run in the development environment.
* No load testing beyond the p95 checks above; no penetration test.
