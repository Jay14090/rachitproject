"""Doctor schedule helpers: slot grid and availability checks."""
from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from .models import Appointment, DoctorAvailability

SLOT_MINUTES = 30


def _mins(t: time) -> int:
    return t.hour * 60 + t.minute


def windows_for(db: Session, doctor_id: int, day: date) -> list[DoctorAvailability]:
    return db.query(DoctorAvailability).filter_by(doctor_id=doctor_id, weekday=day.weekday()).all()


def has_schedule(db: Session, doctor_id: int) -> bool:
    return db.query(DoctorAvailability).filter_by(doctor_id=doctor_id).first() is not None


def slot_is_valid(db: Session, doctor_id: int, day: date, at: time) -> bool:
    """True if `at` is the start of a slot inside one of the doctor's windows that day."""
    for w in windows_for(db, doctor_id, day):
        offset = _mins(at) - _mins(w.start_time)
        if offset >= 0 and _mins(at) + SLOT_MINUTES <= _mins(w.end_time) and offset % SLOT_MINUTES == 0:
            return True
    return False


def free_slots(db: Session, doctor_id: int, day: date) -> list[time]:
    booked = {a.time.replace(second=0, microsecond=0) for a in
              db.query(Appointment).filter_by(doctor_id=doctor_id, date=day, slot_key="active").all()}
    now = datetime.now()
    out: list[time] = []
    for w in sorted(windows_for(db, doctor_id, day), key=lambda w: w.start_time):
        cur = datetime.combine(day, w.start_time)
        end = datetime.combine(day, w.end_time)
        while cur + timedelta(minutes=SLOT_MINUTES) <= end:
            if cur > now and cur.time() not in booked:
                out.append(cur.time())
            cur += timedelta(minutes=SLOT_MINUTES)
    return out
