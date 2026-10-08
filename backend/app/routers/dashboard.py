from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Appointment, Department, Doctor, Patient, Prediction, User

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

    by_dept = (db.query(Department.department_name, func.count(Appointment.appointment_id))
               .select_from(Department)
               .outerjoin(Doctor, Doctor.department_id == Department.department_id)
               .outerjoin(Appointment, (Appointment.doctor_id == Doctor.doctor_id) & (Appointment.status != "cancelled"))
               .group_by(Department.department_name).order_by(Department.department_name).all())

    by_disease = {d: {"count": n, "avg_risk": round(float(avg), 3), "levels": {"low": 0, "moderate": 0, "high": 0}}
                  for d, n, avg in db.query(Prediction.disease_type, func.count(), func.avg(Prediction.risk_score))
                  .group_by(Prediction.disease_type).all()}
    for d, lvl, n in db.query(Prediction.disease_type, Prediction.risk_level, func.count()).group_by(
            Prediction.disease_type, Prediction.risk_level).all():
        by_disease[d]["levels"][lvl] = n

    since = today - timedelta(days=13)
    daily = dict(db.query(func.date(Prediction.created_at), func.count())
                 .filter(Prediction.created_at >= since).group_by(func.date(Prediction.created_at)).all())
    daily_series = [{"date": (since + timedelta(days=i)).isoformat(),
                     "count": int(daily.get((since + timedelta(days=i)).isoformat(), 0))} for i in range(14)]

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
        "appointments_by_department": [{"department": n, "count": c} for n, c in by_dept],
        "risk_distribution": {lvl: risk.get(lvl, 0) for lvl in ("low", "moderate", "high")},
        "predictions_by_disease": by_disease,
        "predictions_last_14_days": daily_series,
    }
