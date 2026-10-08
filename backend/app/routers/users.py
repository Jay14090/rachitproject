from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..audit import log_action
from ..database import get_db
from ..deps import ADMIN, require_roles
from ..models import Doctor, User
from ..schemas import UserCreate, UserOut, UserUpdate
from ..security import hash_password

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_roles(ADMIN))):
    return db.query(User).order_by(User.user_id).all()


@router.post("", response_model=UserOut, status_code=201)
def create_user(body: UserCreate, db: Session = Depends(get_db), actor: User = Depends(require_roles(ADMIN))):
    email = body.email.lower()
    if db.query(User).filter_by(email=email).first():
        raise HTTPException(409, "A user with this email already exists")
    if body.doctor_id is not None and not db.get(Doctor, body.doctor_id):
        raise HTTPException(422, "doctor_id does not exist")
    user = User(name=body.name, email=email, password_hash=hash_password(body.password),
                role=body.role, doctor_id=body.doctor_id)
    db.add(user)
    db.flush()
    log_action(db, actor, "user_created", "user", user.user_id, {"role": user.role})
    db.commit()
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: UserUpdate, db: Session = Depends(get_db),
                actor: User = Depends(require_roles(ADMIN))):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    changes = body.model_dump(exclude_unset=True)
    if user.user_id == actor.user_id and (changes.get("status") == "inactive" or
                                         ("role" in changes and changes["role"] != ADMIN)):
        raise HTTPException(400, "You cannot deactivate or demote your own account")
    if "password" in changes:
        user.password_hash = hash_password(changes.pop("password"))
        changes["password"] = "changed"
    for k, v in changes.items():
        if k != "password":
            setattr(user, k, v)
    log_action(db, actor, "user_updated", "user", user.user_id, {"fields": sorted(changes)})
    db.commit()
    return user
