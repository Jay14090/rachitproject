from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..audit import log_action
from ..database import get_db
from ..deps import ADMIN, DOCTOR, RECEPTION, require_roles
from ..models import Appointment, Doctor, Patient, User
from ..scheduling import SLOT_MINUTES, has_schedule, slot_is_valid
from ..schemas import AppointmentIn, AppointmentOut, AppointmentUpdate

router = APIRouter(prefix="/api/appointments", tags=["appointments"])
ALLOWED = require_roles(ADMIN, DOCTOR, RECEPTION)


def _check_slot_free(db: Session, doctor_id: int, day: date, at, exclude_id: int | None = None) -> None:
    q = db.query(Appointment).filter_by(doctor_id=doctor_id, date=day, time=at, slot_key="active")
    if exclude_id:
        q = q.filter(Appointment.appointment_id != exclude_id)
    if q.first():
        raise HTTPException(409, "That doctor already has an appointment at this date and time")


def _check_not_past(day: date, at) -> None:
    if datetime.combine(day, at) < datetime.now():
        raise HTTPException(422, "Appointment cannot be scheduled in the past")


def _check_schedule(db: Session, doctor_id: int, day: date, at) -> None:
    """If the doctor has a published weekly schedule, the slot must fall on it (and on the slot grid)."""
    if has_schedule(db, doctor_id) and not slot_is_valid(db, doctor_id, day, at):
        raise HTTPException(422, f"Doctor is not available at that time. Choose a free {SLOT_MINUTES}-minute slot "
                                 "inside the doctor's working hours (see /api/doctors/{{id}}/slots).")


def _check_doctor_active(db: Session, doctor_id: int) -> None:
    doc = db.get(Doctor, doctor_id)
    if not doc:
        raise HTTPException(422, "doctor_id does not exist")
    if doc.status != "active":
        raise HTTPException(422, "Doctor is not active")


@router.get("", response_model=list[AppointmentOut])
def list_appointments(date_: date | None = Query(None, alias="date"), status: str | None = None,
                      doctor_id: int | None = None, patient_id: int | None = None,
                      skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500),
                      db: Session = Depends(get_db), _: User = Depends(ALLOWED)):
    q = db.query(Appointment)
    if date_:
        q = q.filter(Appointment.date == date_)
    if status:
        q = q.filter(Appointment.status == status)
    if doctor_id:
        q = q.filter(Appointment.doctor_id == doctor_id)
    if patient_id:
        q = q.filter(Appointment.patient_id == patient_id)
    return q.order_by(Appointment.date.desc(), Appointment.time).offset(skip).limit(limit).all()


@router.post("", response_model=AppointmentOut, status_code=201)
def create_appointment(body: AppointmentIn, db: Session = Depends(get_db), actor: User = Depends(ALLOWED)):
    if not db.get(Patient, body.patient_id):
        raise HTTPException(422, "patient_id does not exist")
    _check_doctor_active(db, body.doctor_id)
    _check_not_past(body.date, body.time)
    _check_schedule(db, body.doctor_id, body.date, body.time)
    _check_slot_free(db, body.doctor_id, body.date, body.time)
    appt = Appointment(**body.model_dump())
    db.add(appt)
    try:
        db.flush()
    except IntegrityError:  # lost a race with a concurrent booking
        db.rollback()
        raise HTTPException(409, "That doctor already has an appointment at this date and time")
    log_action(db, actor, "appointment_created", "appointment", appt.appointment_id)
    db.commit()
    return appt


@router.patch("/{appointment_id}", response_model=AppointmentOut)
def update_appointment(appointment_id: int, body: AppointmentUpdate, db: Session = Depends(get_db),
                       actor: User = Depends(ALLOWED)):
    appt = db.get(Appointment, appointment_id)
    if not appt:
        raise HTTPException(404, "Appointment not found")
    changes = body.model_dump(exclude_unset=True)
    if appt.status != "scheduled" and changes:
        raise HTTPException(409, f"A {appt.status} appointment can no longer be changed")

    new_status = changes.get("status", appt.status)
    new_doctor = changes.get("doctor_id", appt.doctor_id)
    new_date = changes.get("date", appt.date)
    new_time = changes.get("time", appt.time)
    rescheduled = (new_doctor, new_date, new_time) != (appt.doctor_id, appt.date, appt.time)

    if rescheduled:
        if new_status != "scheduled":
            raise HTTPException(422, "Only a scheduled appointment can be rescheduled")
        _check_doctor_active(db, new_doctor)
        _check_not_past(new_date, new_time)
        _check_schedule(db, new_doctor, new_date, new_time)
        _check_slot_free(db, new_doctor, new_date, new_time, exclude_id=appt.appointment_id)

    for k, v in changes.items():
        setattr(appt, k, v)
    appt.slot_key = "active" if appt.status == "scheduled" else None  # free the slot when closed
    if "doctor_id" in changes:
        db.flush()
        db.refresh(appt)
    action = "appointment_rescheduled" if rescheduled else f"appointment_{new_status}" if "status" in changes \
        else "appointment_updated"
    log_action(db, actor, action, "appointment", appointment_id, {"fields": sorted(changes)})
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "That doctor already has an appointment at this date and time")
    return appt
