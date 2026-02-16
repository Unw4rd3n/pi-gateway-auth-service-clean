from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import get_client_ip, get_current_user, get_rate_limiter, get_redis
from ..models import RefreshToken, User
from ..rate_limit import RateLimitExceeded, RedisRateLimiter
from ..schemas import LoginRequest, RefreshRequest, RegisterRequest, TokenPair, UserResponse
from ..security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from ..services.audit import write_audit


router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_token_pair(db: Session, user: User) -> TokenPair:
    access = create_access_token(user.id, user.role)
    refresh = create_refresh_token(user.id, user.role)
    payload = decode_token(refresh)

    db.add(
        RefreshToken(
            user_id=user.id,
            token_jti=payload["jti"],
            expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC).replace(tzinfo=None),
        )
    )
    db.commit()

    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
    limiter: RedisRateLimiter = Depends(get_rate_limiter),
):
    ip = get_client_ip(request)
    try:
        await limiter.enforce(f"register:{ip}", settings.rate_limit_register_per_minute, 60)
    except RateLimitExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    existing = db.query(User).filter(User.email == body.email.lower()).first()
    if existing:
        raise HTTPException(status_code=409, detail="User already exists")

    user = User(email=body.email.lower(), password_hash=hash_password(body.password), role="user")
    db.add(user)
    db.commit()
    db.refresh(user)

    write_audit(db, action="register", detail=f"User registered: {user.email}", user_id=user.id, ip_address=ip)

    return UserResponse(id=user.id, email=user.email, role=user.role, is_active=user.is_active, created_at=user.created_at)


@router.post("/login", response_model=TokenPair)
async def login(
    body: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
    limiter: RedisRateLimiter = Depends(get_rate_limiter),
):
    ip = get_client_ip(request)
    try:
        await limiter.enforce(f"login:{ip}", settings.rate_limit_login_per_minute, 60)
    except RateLimitExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    user = db.query(User).filter(User.email == body.email.lower()).first()
    if not user or not verify_password(body.password, user.password_hash):
        write_audit(db, action="login_failed", detail=f"Failed login: {body.email.lower()}", ip_address=ip)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    tokens = _issue_token_pair(db, user)
    write_audit(db, action="login_success", detail=f"Successful login: {user.email}", user_id=user.id, ip_address=ip)
    return tokens


@router.post("/refresh", response_model=TokenPair)
async def refresh_token(body: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    ip = get_client_ip(request)
    try:
        payload = decode_token(body.refresh_token)
    except Exception as exc:
        write_audit(db, action="refresh_failed", detail="Invalid refresh token", ip_address=ip)
        raise HTTPException(status_code=401, detail="Invalid refresh token") from exc

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    record = db.query(RefreshToken).filter(RefreshToken.token_jti == payload.get("jti")).first()
    if not record or record.revoked or record.expires_at < datetime.utcnow():
        write_audit(db, action="refresh_failed", detail="Refresh token revoked or expired", ip_address=ip)
        raise HTTPException(status_code=401, detail="Refresh token revoked or expired")

    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")

    record.revoked = True
    db.commit()

    tokens = _issue_token_pair(db, user)
    write_audit(db, action="token_refreshed", detail=f"Tokens refreshed for {user.email}", user_id=user.id, ip_address=ip)
    return tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    ip = get_client_ip(request)
    try:
        payload = decode_token(body.refresh_token)
        token_jti = payload.get("jti")
    except Exception:
        return

    record = db.query(RefreshToken).filter(RefreshToken.token_jti == token_jti).first()
    if record and not record.revoked:
        record.revoked = True
        db.commit()
        write_audit(db, action="logout", detail="Refresh token revoked on logout", user_id=record.user_id, ip_address=ip)


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return UserResponse(id=user.id, email=user.email, role=user.role, is_active=user.is_active, created_at=user.created_at)


@router.get("/audit", response_model=list[dict])
async def my_audit(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    events = (
        db.query(User.id, User.email)
        .filter(User.id == user.id)
        .all()
    )
    return [{"user_id": user.id, "email": user.email, "records": len(events)}]
