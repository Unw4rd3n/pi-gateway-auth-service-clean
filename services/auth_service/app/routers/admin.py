from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_roles
from ..models import AuditEvent, User
from ..schemas import AuditEventResponse, UserResponse


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserResponse])
def list_users(_: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.created_at.desc()).limit(200).all()
    return [
        UserResponse(
            id=u.id,
            email=u.email,
            role=u.role,
            is_active=u.is_active,
            created_at=u.created_at,
        )
        for u in users
    ]


@router.get("/audit", response_model=list[AuditEventResponse])
def list_audit_events(_: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    events = db.query(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(500).all()
    return [
        AuditEventResponse(
            id=e.id,
            user_id=e.user_id,
            action=e.action,
            detail=e.detail,
            ip_address=e.ip_address,
            created_at=e.created_at,
        )
        for e in events
    ]
