from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..audit import log_action
from ..database import get_db
from ..deps import ADMIN, get_current_user, require_roles
from ..models import Department, Doctor, DoctorAvailability, User
from ..scheduling import SLOT_MINUTES, free_slots
from ..schemas import AvailabilityWindow, DoctorIn, DoctorOut, DoctorUpdate

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


@router.get("/{doctor_id}/availability", response_model=list[AvailabilityWindow])
def get_availability(doctor_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    if not db.get(Doctor, doctor_id):
        raise HTTPException(404, "Doctor not found")
    return (db.query(DoctorAvailability).filter_by(doctor_id=doctor_id)
            .order_by(DoctorAvailability.weekday, DoctorAvailability.start_time).all())


@router.put("/{doctor_id}/availability", response_model=list[AvailabilityWindow])
def set_availability(doctor_id: int, windows: list[AvailabilityWindow], db: Session = Depends(get_db),
                     actor: User = Depends(require_roles(ADMIN))):
    """Replace the doctor's weekly schedule. An empty list removes the restriction entirely."""
    if not db.get(Doctor, doctor_id):
        raise HTTPException(404, "Doctor not found")
    ordered = sorted(windows, key=lambda w: (w.weekday, w.start_time))
    for a, b in zip(ordered, ordered[1:]):
        if a.weekday == b.weekday and b.start_time < a.end_time:
            raise HTTPException(422, "Availability windows on the same weekday must not overlap")
    db.query(DoctorAvailability).filter_by(doctor_id=doctor_id).delete()
    db.add_all(DoctorAvailability(doctor_id=doctor_id, **w.model_dump()) for w in ordered)
    log_action(db, actor, "doctor_availability_set", "doctor", doctor_id, {"windows": len(ordered)})
    db.commit()
    return ordered


@router.get("/{doctor_id}/slots")
def get_free_slots(doctor_id: int, day: date = Query(..., alias="date"), db: Session = Depends(get_db),
                   _: User = Depends(get_current_user)):
    """Bookable start times (HH:MM) for a doctor on a date. Empty if the doctor does not work that day."""
    if not db.get(Doctor, doctor_id):
        raise HTTPException(404, "Doctor not found")
    return {"date": day, "slot_minutes": SLOT_MINUTES,
            "slots": [t.strftime("%H:%M") for t in free_slots(db, doctor_id, day)]}
