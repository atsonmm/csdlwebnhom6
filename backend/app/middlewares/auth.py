"""Phiên đăng nhập bằng cookie httpOnly + phân quyền — giống server/auth.js của bản Node.

Token phiên ngẫu nhiên chỉ nằm trong cookie của trình duyệt; CSDL chỉ lưu SHA-256 của token,
nên lộ bảng sessions cũng không dùng được để đăng nhập."""
import hashlib
import secrets
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.config.database import get_db
from app.models.users import User, UserSession

COOKIE = "tn_session"
SESSION_TTL = timedelta(days=30)

NEED_LOGIN = "Vui lòng đăng nhập để tiếp tục"
FORBIDDEN = "Tài khoản của bạn không có quyền truy cập khu vực này"


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def new_token() -> str:
    return secrets.token_urlsafe(32)


def public_user(u: User | None) -> dict | None:
    if u is None:
        return None
    return {"id": u.id, "name": u.name, "email": u.email, "phone": u.phone, "role": u.role or "customer"}


def _cookie_kwargs() -> dict:
    secure = settings.env == "prod" if settings.cookie_secure is None else settings.cookie_secure
    return {"httponly": True, "samesite": "lax", "secure": secure, "path": "/"}


def create_session(db: Session, response: Response, user_id: int) -> None:
    token = new_token()
    db.add(UserSession(token_hash=sha256_hex(token), user_id=user_id,
                       expires_at=datetime.now(timezone.utc) + SESSION_TTL))
    db.flush()
    response.set_cookie(COOKIE, token, max_age=int(SESSION_TTL.total_seconds()), **_cookie_kwargs())


def destroy_session(db: Session, request: Request, response: Response) -> None:
    token = request.cookies.get(COOKIE)
    if token:
        db.execute(delete(UserSession).where(UserSession.token_hash == sha256_hex(token)))
    response.delete_cookie(COOKIE, **_cookie_kwargs())


def current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    """Người dùng của phiên hợp lệ (chưa hết hạn), hoặc None"""
    token = request.cookies.get(COOKIE)
    if not token:
        return None
    return db.scalar(
        select(User)
        .join(UserSession, UserSession.user_id == User.id)
        .where(UserSession.token_hash == sha256_hex(token), UserSession.expires_at > datetime.now(timezone.utc))
    )


def require_user(user: User | None = Depends(current_user)) -> User:
    if user is None:
        raise HTTPException(401, NEED_LOGIN)
    return user


def require_role(*roles: str) -> Callable[..., User]:
    """Chỉ cho phép các vai trò được liệt kê: Depends(require_role("admin"))"""

    def dependency(user: User | None = Depends(current_user)) -> User:
        if user is None:
            raise HTTPException(401, NEED_LOGIN)
        if user.role not in roles:
            raise HTTPException(403, FORBIDDEN)
        return user

    return dependency
