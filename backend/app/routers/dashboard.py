from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Appointment, Doctor, Patient, Prediction, User

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Aggregate counts only (no PHI), so every authenticated role may view them."""
    today = date.today()
    week = [today + timedelta(days=i) for i in range(7)]
    appt_status = dict(db.query(Appointment.status, func.count()).group_by(Appointment.status).all())
    upcoming = dict(db.query(Appointment.date, func.count())
                    .filter(Appointment.status == "scheduled", Appointment.date.in_(week))
                    .group_by(Appointment.date).all())
    risk = dict(db.query(Prediction.risk_level, func.count()).group_by(Prediction.risk_level).all())
    return {
        "totals": {
            "patients": db.query(func.count(Patient.patient_id)).scalar(),
            "active_doctors": db.query(func.count(Doctor.doctor_id)).filter(Doctor.status == "active").scalar(),
            "appointments_today": db.query(func.count(Appointment.appointment_id))
                                    .filter(Appointment.date == today, Appointment.status != "cancelled").scalar(),
            "predictions": db.query(func.count(Prediction.prediction_id)).scalar(),
        },
        "appointments_by_status": {s: appt_status.get(s, 0) for s in ("scheduled", "completed", "cancelled")},
        "appointments_next_7_days": [{"date": d.isoformat(), "count": upcoming.get(d, 0)} for d in week],
        "risk_distribution": {lvl: risk.get(lvl, 0) for lvl in ("low", "moderate", "high")},
    }
