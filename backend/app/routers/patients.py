from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..audit import log_action
from ..database import get_db
from ..deps import ADMIN, DOCTOR, RECEPTION, require_roles
from ..models import Patient, User
from ..schemas import PatientIn, PatientOut, PatientUpdate

router = APIRouter(prefix="/api/patients", tags=["patients"])

CAN_READ = require_roles(ADMIN, DOCTOR, RECEPTION)
CAN_WRITE = require_roles(ADMIN, RECEPTION)


@router.get("", response_model=list[PatientOut])
def list_patients(q: str | None = Query(None, max_length=100), skip: int = Query(0, ge=0),
                  limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db), _: User = Depends(CAN_READ)):
    query = db.query(Patient)
    if q:
        like = f"%{q.strip()}%"
        conds = [Patient.name.ilike(like), Patient.contact.ilike(like)]
        if q.strip().isdigit():
            conds.append(Patient.patient_id == int(q.strip()))
        query = query.filter(or_(*conds))
    return query.order_by(Patient.patient_id.desc()).offset(skip).limit(limit).all()


@router.post("", response_model=PatientOut, status_code=201)
def create_patient(body: PatientIn, db: Session = Depends(get_db), actor: User = Depends(CAN_WRITE)):
    patient = Patient(**body.model_dump())
    db.add(patient)
    db.flush()
    log_action(db, actor, "patient_created", "patient", patient.patient_id)
    db.commit()
    return patient


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(patient_id: int, db: Session = Depends(get_db), actor: User = Depends(CAN_READ)):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(404, "Patient not found")
    log_action(db, actor, "patient_viewed", "patient", patient_id)
    db.commit()
    return patient


@router.patch("/{patient_id}", response_model=PatientOut)
def update_patient(patient_id: int, body: PatientUpdate, db: Session = Depends(get_db),
                   actor: User = Depends(CAN_WRITE)):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(404, "Patient not found")
    changes = body.model_dump(exclude_unset=True)
    for k, v in changes.items():
        setattr(patient, k, v)
    log_action(db, actor, "patient_updated", "patient", patient_id, {"fields": sorted(changes)})
    db.commit()
    return patient
