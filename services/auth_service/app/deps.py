from collections.abc import Generator

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import User
from .rate_limit import RedisRateLimiter
from .security import decode_token


bearer_scheme = HTTPBearer(auto_error=False)
_redis_client: Redis | None = None


def get_redis() -> Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


def get_rate_limiter(redis: Redis = Depends(get_redis)) -> RedisRateLimiter:
    return RedisRateLimiter(redis)


def _unauthorized() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing token")


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise _unauthorized()

    try:
        payload = decode_token(credentials.credentials)
    except Exception as exc:
        raise _unauthorized() from exc

    if payload.get("type") != "access":
        raise _unauthorized()

    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user or not user.is_active:
        raise _unauthorized()

    return user


def require_roles(*roles: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return checker


def get_client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def db_session() -> Generator[Session, None, None]:
    yield from get_db()
