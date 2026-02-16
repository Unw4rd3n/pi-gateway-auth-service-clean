from sqlalchemy.orm import Session

from ..models import AuditEvent


def write_audit(db: Session, action: str, detail: str, user_id: str | None = None, ip_address: str | None = None) -> None:
    event = AuditEvent(user_id=user_id, action=action, detail=detail, ip_address=ip_address)
    db.add(event)
    db.commit()
