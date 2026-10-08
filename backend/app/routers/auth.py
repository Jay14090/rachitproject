from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..audit import log_action
from ..database import get_db
from ..deps import get_current_user
from ..models import LoginThrottle, User, utcnow
from ..schemas import ChangePasswordIn, LoginIn, LoginOut, UserOut
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

MAX_FAILED_ATTEMPTS = 5
LOCK_MINUTES = 15

# Verified against when the email is unknown, so response time doesn't reveal which emails exist.
_DUMMY_HASH = hash_password("not-a-real-password")


@router.post("/login", response_model=LoginOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    email = body.email.lower()
    throttle = db.get(LoginThrottle, email)
    if throttle and throttle.locked_until and throttle.locked_until > utcnow():
        mins = int((throttle.locked_until - utcnow()).total_seconds() // 60) + 1
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            f"Too many failed attempts. Try again in about {mins} minute(s).")

    user = db.query(User).filter(User.email == email).first()
    ok = verify_password(body.password, user.password_hash if user else _DUMMY_HASH)
    if not user or not ok or user.status != "active":
        if throttle is None:
            throttle = LoginThrottle(email=email, failed_attempts=0)
            db.add(throttle)
        # An expired lock starts a fresh count.
        if throttle.locked_until and throttle.locked_until <= utcnow():
            throttle.failed_attempts, throttle.locked_until = 0, None
        throttle.failed_attempts += 1
        locked = throttle.failed_attempts >= MAX_FAILED_ATTEMPTS
        if locked:
            throttle.locked_until = utcnow() + timedelta(minutes=LOCK_MINUTES)
        log_action(db, None, "login_locked" if locked else "login_failed", "user", None,
                   {"attempts": throttle.failed_attempts})
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    if throttle:
        db.delete(throttle)
    log_action(db, user, "login", "user", user.user_id)
    db.commit()
    return LoginOut(access_token=create_access_token(user.user_id, user.role), user=user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/change-password", status_code=204)
def change_password(body: ChangePasswordIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    if body.new_password == body.current_password:
        raise HTTPException(422, "New password must differ from the current one")
    user.password_hash = hash_password(body.new_password)
    log_action(db, user, "password_changed", "user", user.user_id)
    db.commit()
