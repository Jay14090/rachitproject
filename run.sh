#!/usr/bin/env bash
# One-command local run: sets up deps on first use, then starts API (:8000) and UI (:5173).
set -e
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -r backend/requirements.txt
[ -f ml/artifacts/diabetes_model.joblib ] || .venv/bin/python ml/train_diabetes.py
[ -d frontend/node_modules ] || (cd frontend && npm install --no-audit --no-fund)
trap 'kill 0' EXIT
(cd backend && ../.venv/bin/uvicorn app.main:app --port 8000) &
(cd frontend && npm run dev -- --host 127.0.0.1) &
echo "UI: http://localhost:5173   API docs: http://localhost:8000/docs"
wait
