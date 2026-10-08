from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..audit import log_action
from ..database import get_db
from ..deps import ADMIN, ANALYST, DOCTOR, require_roles
from ..ml_service import get_diabetes_model
from ..models import ModelVersion, Patient, Prediction, PredictionInput, User
from ..schemas import DiabetesInput, ModelVersionOut, PredictionOut

router = APIRouter(tags=["predictions"])


@router.post("/api/predict/diabetes", response_model=PredictionOut, status_code=201)
def predict_diabetes(body: DiabetesInput, db: Session = Depends(get_db),
                     actor: User = Depends(require_roles(ADMIN, DOCTOR))):
    if not db.get(Patient, body.patient_id):
        raise HTTPException(422, "patient_id does not exist")
    try:
        model = get_diabetes_model()
    except FileNotFoundError:
        raise HTTPException(503, "Prediction model is not available. Train it with `python ml/train_diabetes.py`.")
    values = body.model_dump(exclude={"patient_id"})
    out = model.predict(values)
    pred = Prediction(patient_id=body.patient_id, requested_by=actor.user_id, disease_type="diabetes",
                      result=out["result"], risk_score=out["risk_score"], risk_level=out["risk_level"],
                      model_version=model.version, explanation=out["explanation"],
                      inputs=PredictionInput(inputs=values))
    db.add(pred)
    db.flush()
    log_action(db, actor, "prediction_created", "prediction", pred.prediction_id,
               {"disease": "diabetes", "patient_id": body.patient_id, "model_version": model.version})
    db.commit()
    return _serialize(pred)


@router.get("/api/predictions/{patient_id}", response_model=list[PredictionOut])
def prediction_history(patient_id: int, db: Session = Depends(get_db),
                       actor: User = Depends(require_roles(ADMIN, DOCTOR))):
    if not db.get(Patient, patient_id):
        raise HTTPException(404, "Patient not found")
    log_action(db, actor, "predictions_viewed", "patient", patient_id)
    db.commit()
    rows = db.query(Prediction).filter_by(patient_id=patient_id).order_by(Prediction.created_at.desc()).all()
    return [_serialize(r) for r in rows]


@router.get("/api/models", response_model=list[ModelVersionOut])
def list_models(db: Session = Depends(get_db), _: User = Depends(require_roles(ADMIN, DOCTOR, ANALYST))):
    return db.query(ModelVersion).order_by(ModelVersion.trained_at.desc()).all()


def _serialize(p: Prediction) -> PredictionOut:
    return PredictionOut(prediction_id=p.prediction_id, patient_id=p.patient_id, disease_type=p.disease_type,
                         result=p.result, risk_score=p.risk_score, risk_level=p.risk_level,
                         model_version=p.model_version, explanation=p.explanation,
                         inputs=p.inputs.inputs if p.inputs else {}, created_at=p.created_at)
