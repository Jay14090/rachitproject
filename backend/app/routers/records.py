from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..audit import log_action
from ..database import get_db
from ..deps import ADMIN, DOCTOR, require_roles
from ..models import Doctor, MedicalRecord, Patient, User
from ..schemas import MedicalRecordIn, MedicalRecordOut

router = APIRouter(prefix="/api/medical-records", tags=["medical-records"])


@router.post("", response_model=MedicalRecordOut, status_code=201)
def create_record(body: MedicalRecordIn, db: Session = Depends(get_db),
                  actor: User = Depends(require_roles(ADMIN, DOCTOR))):
    if not db.get(Patient, body.patient_id):
        raise HTTPException(422, "patient_id does not exist")
    if not (body.measurements or body.symptoms or body.notes):
        raise HTTPException(422, "Provide at least one of measurements, symptoms or notes")
    doctor_id = body.doctor_id or actor.doctor_id
    if doctor_id is not None and not db.get(Doctor, doctor_id):
        raise HTTPException(422, "doctor_id does not exist")
    rec = MedicalRecord(patient_id=body.patient_id, doctor_id=doctor_id, measurements=body.measurements,
                        symptoms=body.symptoms, notes=body.notes)
    db.add(rec)
    db.flush()
    log_action(db, actor, "medical_record_created", "medical_record", rec.record_id,
               {"patient_id": body.patient_id})
    db.commit()
    db.refresh(rec)
    return rec


@router.get("/patient/{patient_id}", response_model=list[MedicalRecordOut])
def patient_records(patient_id: int, db: Session = Depends(get_db),
                    actor: User = Depends(require_roles(ADMIN, DOCTOR))):
    if not db.get(Patient, patient_id):
        raise HTTPException(404, "Patient not found")
    log_action(db, actor, "medical_records_viewed", "patient", patient_id)
    db.commit()
    return db.query(MedicalRecord).filter_by(patient_id=patient_id).order_by(MedicalRecord.created_at.desc()).all()
