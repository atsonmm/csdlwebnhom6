"""Controller — xử lý request/response cho routers/auth.py: API tài khoản — giống /api/auth/* của server Node (đường dẫn, JSON, mã lỗi, câu báo lỗi)"""
import logging
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Request, Response
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.middlewares.auth import create_session, destroy_session, new_token, public_user, sha256_hex
from app.config.settings import settings
from app.models.users import PasswordReset, User, UserSession
from app.middlewares.ratelimit import LoginLimiter
from app.utils.security import hash_password, verify_password
from app.utils.validators import as_str, check_password, parse_identifier
from app.schemas.auth import RegisterIn, LoginIn, ForgotIn, ResetIn


BAD_NAME = "Vui lòng nhập họ và tên (2–80 ký tự)"

BAD_IDENTIFIER = "Email hoặc số điện thoại không hợp lệ"

DUP_EMAIL = "Email này đã được đăng ký"

DUP_PHONE = "Số điện thoại này đã được đăng ký"

def find_user(db: Session, ident: dict) -> User | None:
    if "email" in ident:
        return db.scalar(select(User).where(User.email == ident["email"]))
    return db.scalar(select(User).where(User.phone == ident["phone"]))

def _duplicate(ident: dict) -> HTTPException:
    return HTTPException(409, DUP_EMAIL if "email" in ident else DUP_PHONE)

MISSING_LOGIN = "Vui lòng nhập email/số điện thoại và mật khẩu"

BAD_CREDENTIALS = "Email/số điện thoại hoặc mật khẩu không đúng"

DUMMY_HASH = hash_password(secrets.token_hex(12))

RESET_TTL = timedelta(minutes=15)

RESET_INVALID = "Liên kết đặt lại mật khẩu đã hết hạn hoặc không hợp lệ"

log = logging.getLogger("ticketnhip.auth")


def me(user: User | None) -> dict:
    # GET /me
    return {"user": public_user(user)}


def register(body: RegisterIn, response: Response, db: Session) -> dict:
    # POST /register
    name = as_str(body.name).strip()
    if not 2 <= len(name) <= 80:
        raise HTTPException(400, BAD_NAME)
    ident = parse_identifier(body.identifier)
    if ident is None:
        raise HTTPException(400, BAD_IDENTIFIER)
    password = as_str(body.password)
    check_password(password)
    if find_user(db, ident):
        raise _duplicate(ident)

    user = User(name=name, email=ident.get("email"), phone=ident.get("phone"), password_hash=hash_password(password))
    db.add(user)
    try:
        db.flush()
    except IntegrityError:  # hai yêu cầu đăng ký cùng lúc
        db.rollback()
        raise _duplicate(ident) from None
    create_session(db, response, user.id)
    db.commit()
    return {"user": public_user(user)}


def logout(request: Request, response: Response, db: Session) -> dict:
    # POST /logout
    destroy_session(db, request, response)
    db.commit()
    return {"ok": True}


def login(body: LoginIn, request: Request, response: Response, db: Session, limiter: LoginLimiter) -> dict:
    # POST /login
    ident = parse_identifier(body.identifier)
    password = as_str(body.password)
    if ident is None or not password:
        raise HTTPException(400, MISSING_LOGIN)

    client_ip = request.client.host if request.client else "?"
    key = f"{client_ip}|{ident.get('email') or ident.get('phone')}"
    limiter.check(key)

    user = find_user(db, ident)
    ok = verify_password(password, user.password_hash if user else DUMMY_HASH)
    if user is None or not ok:
        limiter.fail(key)
        raise HTTPException(401, BAD_CREDENTIALS)
    limiter.clear(key)
    create_session(db, response, user.id)
    db.commit()
    return {"user": public_user(user)}


def forgot(body: ForgotIn, request: Request, db: Session) -> dict:
    # POST /forgot
    ident = parse_identifier(body.identifier)
    if ident is None:
        raise HTTPException(400, BAD_IDENTIFIER)
    out: dict = {"ok": True}
    user = find_user(db, ident)
    if user is not None:
        token = new_token()
        db.add(PasswordReset(token_hash=sha256_hex(token), user_id=user.id,
                             expires_at=datetime.now(timezone.utc) + RESET_TTL))
        db.commit()
        url = f"{str(request.base_url).rstrip('/')}/?reset={token}"
        # Chưa có dịch vụ gửi email/SMS: ghi liên kết ra log máy chủ
        log.warning("[ĐẶT LẠI MẬT KHẨU] %s %s", user.email or user.phone, url)
        if settings.env == "dev":
            out["devResetUrl"] = url
    # Luôn trả cùng một dạng để không lộ tài khoản nào tồn tại
    return out


def reset(body: ResetIn, response: Response, db: Session) -> dict:
    # POST /reset
    token = as_str(body.token)
    token_hash = sha256_hex(token) if token else None
    now = datetime.now(timezone.utc)
    row = db.get(PasswordReset, token_hash) if token_hash else None
    if row is None or row.used or row.expires_at <= now:
        raise HTTPException(400, RESET_INVALID)
    password = as_str(body.password)
    check_password(password)  # mật khẩu sai quy tắc → token vẫn còn dùng được

    # Giành token NGUYÊN TỬ: chỉ một yêu cầu đổi được used false → true,
    # các yêu cầu song song khác nhận None → 400 (liên kết chỉ dùng 1 lần)
    user_id = db.scalar(
        update(PasswordReset)
        .where(PasswordReset.token_hash == token_hash, PasswordReset.used.is_(False), PasswordReset.expires_at > now)
        .values(used=True)
        .returning(PasswordReset.user_id)
    )
    if user_id is None:
        db.rollback()
        raise HTTPException(400, RESET_INVALID)

    # Cùng giao dịch: đổi mật khẩu, đăng xuất mọi thiết bị, tạo phiên mới
    user = db.get(User, user_id)
    user.password_hash = hash_password(password)
    db.execute(delete(UserSession).where(UserSession.user_id == user.id))
    create_session(db, response, user.id)
    db.commit()
    return {"user": public_user(user)}
