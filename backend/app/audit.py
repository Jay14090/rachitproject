from sqlalchemy.orm import Session

from .models import AuditLog, User


def log_action(db: Session, user: User | None, action: str, entity_type: str | None = None,
               entity_id: int | str | None = None, metadata: dict | None = None) -> None:
    """Adds an audit row to the caller's session; it commits together with the change itself."""
    db.add(AuditLog(user_id=user.user_id if user else None, action=action, entity_type=entity_type,
                    entity_id=str(entity_id) if entity_id is not None else None, log_metadata=metadata))
