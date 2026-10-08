import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..audit import log_action
from ..database import get_db
from ..deps import ADMIN, ANALYST, DOCTOR, require_roles
from ..ml_service import get_model
from ..models import ModelVersion, Patient, Prediction, PredictionInput, User
from ..schemas import DiabetesInput, HeartInput, ModelUsageOut, ModelVersionOut, PredictionOut

router = APIRouter(tags=["predictions"])
CLINICAL = require_roles(ADMIN, DOCTOR)


def _run_prediction(db: Session, actor: User, disease: str, patient_id: int, values: dict) -> PredictionOut:
    if not db.get(Patient, patient_id):
        raise HTTPException(422, "patient_id does not exist")
    try:
        model = get_model(disease)
    except FileNotFoundError:
        raise HTTPException(503, "Prediction model is not available. Train it with the matching ml/train_*.py script.")
    out = model.predict(values)
    pred = Prediction(patient_id=patient_id, requested_by=actor.user_id, disease_type=disease,
                      result=out["result"], risk_score=out["risk_score"], risk_level=out["risk_level"],
                      model_version=model.version, explanation=out["explanation"],
                      inputs=PredictionInput(inputs=values))
    db.add(pred)
    db.flush()
    log_action(db, actor, "prediction_created", "prediction", pred.prediction_id,
               {"disease": disease, "patient_id": patient_id, "model_version": model.version})
    db.commit()
    return _serialize(pred)


@router.post("/api/predict/diabetes", response_model=PredictionOut, status_code=201)
def predict_diabetes(body: DiabetesInput, db: Session = Depends(get_db), actor: User = Depends(CLINICAL)):
    return _run_prediction(db, actor, "diabetes", body.patient_id, body.model_dump(exclude={"patient_id"}))


@router.post("/api/predict/heart-disease", response_model=PredictionOut, status_code=201)
def predict_heart(body: HeartInput, db: Session = Depends(get_db), actor: User = Depends(CLINICAL)):
    return _run_prediction(db, actor, "heart_disease", body.patient_id, body.model_dump(exclude={"patient_id"}))


@router.get("/api/predictions/{patient_id}", response_model=list[PredictionOut])
def prediction_history(patient_id: int, disease: str | None = None, db: Session = Depends(get_db),
                       actor: User = Depends(CLINICAL)):
    if not db.get(Patient, patient_id):
        raise HTTPException(404, "Patient not found")
    log_action(db, actor, "predictions_viewed", "patient", patient_id)
    db.commit()
    q = db.query(Prediction).filter_by(patient_id=patient_id)
    if disease:
        q = q.filter_by(disease_type=disease)
    return [_serialize(r) for r in q.order_by(Prediction.created_at.desc(), Prediction.prediction_id.desc()).all()]


@router.get("/api/models", response_model=list[ModelVersionOut])
def list_models(db: Session = Depends(get_db), _: User = Depends(require_roles(ADMIN, DOCTOR, ANALYST))):
    return db.query(ModelVersion).order_by(ModelVersion.disease_type, ModelVersion.trained_at.desc()).all()


@router.get("/api/models/usage", response_model=list[ModelUsageOut])
def model_usage(db: Session = Depends(get_db), _: User = Depends(require_roles(ADMIN, DOCTOR, ANALYST))):
    """Lightweight monitoring: how often each model version is used and what it tends to output."""
    rows = (db.query(Prediction.model_version, Prediction.disease_type, func.count(), func.avg(Prediction.risk_score),
                     func.max(Prediction.created_at))
            .group_by(Prediction.model_version, Prediction.disease_type).all())
    levels = {}
    for ver, lvl, n in db.query(Prediction.model_version, Prediction.risk_level, func.count()).group_by(
            Prediction.model_version, Prediction.risk_level).all():
        levels.setdefault(ver, {})[lvl] = n
    return [ModelUsageOut(model_version=v, disease_type=d, prediction_count=n, avg_risk_score=round(float(a), 4),
                          last_used=last, risk_levels={k: levels.get(v, {}).get(k, 0) for k in ("low", "moderate", "high")})
            for v, d, n, a, last in rows]


@router.get("/api/reports/predictions.csv")
def export_predictions(db: Session = Depends(get_db), actor: User = Depends(require_roles(ADMIN, ANALYST))):
    """De-identified export (patient_id only, no names/contact) for analysis."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["prediction_id", "patient_id", "disease_type", "risk_score", "risk_level", "model_version", "created_at"])
    for p in db.query(Prediction).order_by(Prediction.prediction_id).all():
        w.writerow([p.prediction_id, p.patient_id, p.disease_type, p.risk_score, p.risk_level, p.model_version,
                    p.created_at.isoformat(timespec="seconds")])
    log_action(db, actor, "predictions_exported", "report", None)
    db.commit()
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="predictions-{datetime.now():%Y%m%d}.csv"'})


def _serialize(p: Prediction) -> PredictionOut:
    return PredictionOut(prediction_id=p.prediction_id, patient_id=p.patient_id, disease_type=p.disease_type,
                         result=p.result, risk_score=p.risk_score, risk_level=p.risk_level,
                         model_version=p.model_version, explanation=p.explanation,
                         inputs=p.inputs.inputs if p.inputs else {}, created_at=p.created_at)
