"""SQLAlchemy models — mirrors the tables in doc section 10."""
from datetime import date, datetime, time, timezone

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Department(Base):
    __tablename__ = "departments"
    department_id: Mapped[int] = mapped_column(primary_key=True)
    department_name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(String(255))


class Doctor(Base):
    __tablename__ = "doctors"
    doctor_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    specialization: Mapped[str] = mapped_column(String(120))
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.department_id"))
    status: Mapped[str] = mapped_column(String(20), default="active")  # active | inactive
    department: Mapped[Department] = relationship(lazy="joined")


class User(Base):
    __tablename__ = "users"
    user_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(190), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20))  # admin | doctor | reception | analyst
    status: Mapped[str] = mapped_column(String(20), default="active")
    doctor_id: Mapped[int | None] = mapped_column(ForeignKey("doctors.doctor_id"))


class Patient(Base):
    __tablename__ = "patients"
    patient_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    date_of_birth: Mapped[date] = mapped_column(Date)
    gender: Mapped[str] = mapped_column(String(10))
    contact: Mapped[str] = mapped_column(String(40))
    address: Mapped[str | None] = mapped_column(String(255))
    registration_date: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    @property
    def age(self) -> int:
        today = date.today()
        dob = self.date_of_birth
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (UniqueConstraint("doctor_id", "date", "time", "slot_key", name="uq_doctor_slot"),)
    appointment_id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.patient_id"), index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.doctor_id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    time: Mapped[time] = mapped_column(Time)
    status: Mapped[str] = mapped_column(String(20), default="scheduled")  # scheduled | completed | cancelled
    # "active" while the slot is held, NULL once cancelled/completed -> frees the slot for re-booking.
    slot_key: Mapped[str | None] = mapped_column(String(10), default="active")
    purpose: Mapped[str | None] = mapped_column(String(255))
    patient: Mapped[Patient] = relationship(lazy="joined")
    doctor: Mapped[Doctor] = relationship(lazy="joined")

    @property
    def patient_name(self) -> str:
        return self.patient.name

    @property
    def doctor_name(self) -> str:
        return self.doctor.name


class MedicalRecord(Base):
    __tablename__ = "medical_records"
    record_id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.patient_id"), index=True)
    doctor_id: Mapped[int | None] = mapped_column(ForeignKey("doctors.doctor_id"))
    measurements: Mapped[dict | None] = mapped_column(JSON)  # e.g. {"bp_systolic": 120, "weight_kg": 70}
    symptoms: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    doctor: Mapped[Doctor | None] = relationship(lazy="joined")

    @property
    def doctor_name(self) -> str | None:
        return self.doctor.name if self.doctor else None


class ModelVersion(Base):
    __tablename__ = "model_versions"
    model_id: Mapped[int] = mapped_column(primary_key=True)
    disease_type: Mapped[str] = mapped_column(String(40))
    algorithm: Mapped[str] = mapped_column(String(60))
    version: Mapped[str] = mapped_column(String(80), unique=True)
    metrics: Mapped[dict] = mapped_column(JSON)
    trained_at: Mapped[datetime] = mapped_column(DateTime)
    active_flag: Mapped[bool] = mapped_column(Boolean, default=True)


class Prediction(Base):
    __tablename__ = "predictions"
    prediction_id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.patient_id"), index=True)
    requested_by: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))
    disease_type: Mapped[str] = mapped_column(String(40))
    result: Mapped[str] = mapped_column(String(30))  # "higher risk" | "lower risk"
    risk_score: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(20))  # low | moderate | high
    model_version: Mapped[str] = mapped_column(String(80))
    explanation: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    inputs: Mapped["PredictionInput"] = relationship(back_populates="prediction", uselist=False,
                                                     cascade="all, delete-orphan", lazy="joined")


class PredictionInput(Base):
    __tablename__ = "prediction_inputs"
    input_id: Mapped[int] = mapped_column(primary_key=True)
    prediction_id: Mapped[int] = mapped_column(ForeignKey("predictions.prediction_id"), unique=True)
    inputs: Mapped[dict] = mapped_column(JSON)
    prediction: Mapped[Prediction] = relationship(back_populates="inputs")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    log_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"), index=True)
    action: Mapped[str] = mapped_column(String(60), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(40))
    entity_id: Mapped[str | None] = mapped_column(String(40))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    # Never put PHI (names, contact, clinical values) in here — IDs and changed field names only.
    log_metadata: Mapped[dict | None] = mapped_column("metadata", JSON)
    user: Mapped[User | None] = relationship(lazy="joined")
