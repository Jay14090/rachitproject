from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..audit import log_action
from ..database import get_db
from ..deps import ADMIN, get_current_user, require_roles
from ..models import Department, Doctor, User
from ..schemas import DepartmentIn, DepartmentOut

router = APIRouter(prefix="/api/departments", tags=["departments"])


@router.get("", response_model=list[DepartmentOut])
def list_departments(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Department).order_by(Department.department_name).all()


@router.post("", response_model=DepartmentOut, status_code=201)
def create_department(body: DepartmentIn, db: Session = Depends(get_db), actor: User = Depends(require_roles(ADMIN))):
    if db.query(Department).filter_by(department_name=body.department_name).first():
        raise HTTPException(409, "Department already exists")
    dept = Department(**body.model_dump())
    db.add(dept)
    db.flush()
    log_action(db, actor, "department_created", "department", dept.department_id)
    db.commit()
    return dept


@router.put("/{department_id}", response_model=DepartmentOut)
def update_department(department_id: int, body: DepartmentIn, db: Session = Depends(get_db),
                      actor: User = Depends(require_roles(ADMIN))):
    dept = db.get(Department, department_id)
    if not dept:
        raise HTTPException(404, "Department not found")
    for k, v in body.model_dump().items():
        setattr(dept, k, v)
    log_action(db, actor, "department_updated", "department", department_id)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Department name already in use")
    return dept


@router.delete("/{department_id}", status_code=204)
def delete_department(department_id: int, db: Session = Depends(get_db), actor: User = Depends(require_roles(ADMIN))):
    dept = db.get(Department, department_id)
    if not dept:
        raise HTTPException(404, "Department not found")
    if db.query(Doctor).filter_by(department_id=department_id).count():
        raise HTTPException(409, "Department still has doctors assigned")
    db.delete(dept)
    log_action(db, actor, "department_deleted", "department", department_id)
    db.commit()
