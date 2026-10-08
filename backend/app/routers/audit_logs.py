from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import ADMIN, require_roles
from ..models import AuditLog, User

router = APIRouter(prefix="/api/audit-logs", tags=["audit"])


@router.get("")
def list_audit_logs(action: str | None = None, user_id: int | None = None, skip: int = Query(0, ge=0),
                    limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db),
                    _: User = Depends(require_roles(ADMIN))):
    q = db.query(AuditLog)
    if action:
        q = q.filter(AuditLog.action == action)
    if user_id:
        q = q.filter(AuditLog.user_id == user_id)
    rows = q.order_by(AuditLog.log_id.desc()).offset(skip).limit(limit).all()
    return [{"log_id": r.log_id, "timestamp": r.timestamp, "user_id": r.user_id,
             "user_name": r.user.name if r.user else None, "action": r.action,
             "entity_type": r.entity_type, "entity_id": r.entity_id, "metadata": r.log_metadata}
            for r in rows]
