import datetime as dt
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

Role = Literal["admin", "doctor", "reception", "analyst"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- auth / users
class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(ORM):
    user_id: int
    name: str
    email: str
    role: str
    status: str
    doctor_id: int | None = None


class LoginOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: Role
    doctor_id: int | None = None


class UserUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=120)
    role: Role | None = None
    status: Literal["active", "inactive"] | None = None
    password: str | None = Field(None, min_length=8, max_length=128)
    doctor_id: int | None = None


# ---- departments / doctors
class DepartmentIn(BaseModel):
    department_name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(None, max_length=255)


class DepartmentOut(ORM, DepartmentIn):
    department_id: int


class DoctorIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    specialization: str = Field(min_length=2, max_length=120)
    department_id: int
    status: Literal["active", "inactive"] = "active"


class DoctorUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=120)
    specialization: str | None = Field(None, min_length=2, max_length=120)
    department_id: int | None = None
    status: Literal["active", "inactive"] | None = None


class DoctorOut(ORM):
    doctor_id: int
    name: str
    specialization: str
    department_id: int
    status: str
    department: DepartmentOut


# ---- patients
class PatientIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    date_of_birth: date
    gender: Literal["male", "female", "other"]
    contact: str = Field(min_length=5, max_length=40, pattern=r"^[0-9+()\-\s]+$")
    address: str | None = Field(None, max_length=255)

    @field_validator("date_of_birth")
    @classmethod
    def dob_not_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("date_of_birth cannot be in the future")
        return v


class PatientUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=120)
    date_of_birth: date | None = None
    gender: Literal["male", "female", "other"] | None = None
    contact: str | None = Field(None, min_length=5, max_length=40, pattern=r"^[0-9+()\-\s]+$")
    address: str | None = Field(None, max_length=255)

    @field_validator("date_of_birth")
    @classmethod
    def dob_not_future(cls, v: date | None) -> date | None:
        if v is not None and v > date.today():
            raise ValueError("date_of_birth cannot be in the future")
        return v


class PatientOut(ORM):
    patient_id: int
    name: str
    date_of_birth: date
    gender: str
    contact: str
    address: str | None
    registration_date: datetime
    age: int


# ---- appointments
class AppointmentIn(BaseModel):
    patient_id: int
    doctor_id: int
    date: dt.date
    time: dt.time
    purpose: str | None = Field(None, max_length=255)


class AppointmentUpdate(BaseModel):
    """Status change and/or reschedule."""
    status: Literal["scheduled", "completed", "cancelled"] | None = None
    date: dt.date | None = None
    time: dt.time | None = None
    doctor_id: int | None = None
    purpose: str | None = Field(None, max_length=255)


class AppointmentOut(ORM):
    appointment_id: int
    patient_id: int
    patient_name: str
    doctor_id: int
    doctor_name: str
    date: dt.date
    time: dt.time
    status: str
    purpose: str | None


# ---- medical records
class MedicalRecordIn(BaseModel):
    patient_id: int
    measurements: dict[str, float] | None = None
    symptoms: str | None = Field(None, max_length=2000)
    notes: str | None = Field(None, max_length=5000)
    doctor_id: int | None = None  # defaults to the logged-in doctor's profile


class MedicalRecordOut(ORM):
    record_id: int
    patient_id: int
    doctor_id: int | None
    doctor_name: str | None
    measurements: dict | None
    symptoms: str | None
    notes: str | None
    created_at: datetime


# ---- predictions
class DiabetesInput(BaseModel):
    patient_id: int
    pregnancies: int = Field(ge=0, le=20)
    glucose: float = Field(ge=40, le=400, description="Plasma glucose (mg/dL)")
    blood_pressure: float = Field(ge=30, le=200, description="Diastolic BP (mm Hg)")
    skin_thickness: float = Field(ge=0, le=100, description="Triceps skin fold (mm)")
    insulin: float = Field(ge=0, le=900, description="2-hour serum insulin (mu U/ml)")
    bmi: float = Field(ge=10, le=70)
    diabetes_pedigree: float = Field(ge=0.0, le=3.0)
    age: int = Field(ge=1, le=120)


class Contribution(BaseModel):
    feature: str
    value: float
    impact: float  # change in risk probability attributable to this feature (+ raises, - lowers)


class PredictionOut(ORM):
    prediction_id: int
    patient_id: int
    disease_type: str
    result: str
    risk_score: float
    risk_level: str
    model_version: str
    explanation: list | None
    inputs: dict
    created_at: datetime
    disclaimer: str = ("Model-generated risk estimate for decision support only. "
                       "It is not a medical diagnosis.")


class ModelVersionOut(ORM):
    model_id: int
    disease_type: str
    algorithm: str
    version: str
    metrics: dict
    trained_at: datetime
    active_flag: bool
