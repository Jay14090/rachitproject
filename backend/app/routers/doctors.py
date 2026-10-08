from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..audit import log_action
from ..database import get_db
from ..deps import ADMIN, get_current_user, require_roles
from ..models import Department, Doctor, User
from ..schemas import DoctorIn, DoctorOut, DoctorUpdate

router = APIRouter(prefix="/api/doctors", tags=["doctors"])


@router.get("", response_model=list[DoctorOut])
def list_doctors(department_id: int | None = None, active_only: bool = False,
                 db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    q = db.query(Doctor)
    if department_id:
        q = q.filter(Doctor.department_id == department_id)
    if active_only:
        q = q.filter(Doctor.status == "active")
    return q.order_by(Doctor.name).all()


@router.post("", response_model=DoctorOut, status_code=201)
def create_doctor(body: DoctorIn, db: Session = Depends(get_db), actor: User = Depends(require_roles(ADMIN))):
    if not db.get(Department, body.department_id):
        raise HTTPException(422, "department_id does not exist")
    doc = Doctor(**body.model_dump())
    db.add(doc)
    db.flush()
    log_action(db, actor, "doctor_created", "doctor", doc.doctor_id)
    db.commit()
    db.refresh(doc)
    return doc


@router.patch("/{doctor_id}", response_model=DoctorOut)
def update_doctor(doctor_id: int, body: DoctorUpdate, db: Session = Depends(get_db),
                  actor: User = Depends(require_roles(ADMIN))):
    doc = db.get(Doctor, doctor_id)
    if not doc:
        raise HTTPException(404, "Doctor not found")
    changes = body.model_dump(exclude_unset=True)
    if "department_id" in changes and not db.get(Department, changes["department_id"]):
        raise HTTPException(422, "department_id does not exist")
    for k, v in changes.items():
        setattr(doc, k, v)
    log_action(db, actor, "doctor_updated", "doctor", doctor_id, {"fields": sorted(changes)})
    db.commit()
    db.refresh(doc)
    return doc
