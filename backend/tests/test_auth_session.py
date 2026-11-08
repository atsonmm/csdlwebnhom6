"""Phiên đăng nhập (cookie tn_session), phân quyền, chỉ nhận JSON khi ghi dữ liệu"""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import APIRouter, Depends, Response
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.middlewares.auth import COOKIE, create_session, require_role, require_user, sha256_hex
from app.config.database import get_db
from app.main import app
from app.models.users import User, UserSession

probe = APIRouter(prefix="/api/_probe")


@probe.get("/me")
def _me(user: User = Depends(require_user)) -> dict:
    return {"id": user.id, "role": user.role}


@probe.get("/admin")
def _admin(user: User = Depends(require_role("admin"))) -> dict:
    return {"ok": True}


@probe.post("/echo")
def _echo() -> dict:
    return {"ok": True}


@pytest.fixture
def auth_db(engine, schema):
    with Session(engine) as s:
        yield s
        s.rollback()
        s.execute(delete(User).where(User.email.like("%@phien.vn")))
        s.commit()


@pytest.fixture
def probe_client(engine, auth_db):
    def override():
        with Session(engine) as s:
            yield s

    app.include_router(probe)
    app.dependency_overrides[get_db] = override
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.router.routes[:] = [r for r in app.router.routes if not getattr(r, "path", "").startswith("/api/_probe")]


def login_as(db: Session, client: TestClient, role: str = "customer") -> tuple[User, str, str]:
    """Tạo user + phiên bằng create_session; gắn cookie vào client. Trả (user, token, set-cookie header)."""
    u = User(name="Người thử", email=f"{role}@phien.vn", password_hash="h", role=role)
    db.add(u)
    db.commit()
    resp = Response()
    create_session(db, resp, u.id)
    db.commit()
    header = resp.headers["set-cookie"]
    token = header.split(";", 1)[0].split("=", 1)[1]
    client.cookies.set(COOKIE, token)
    return u, token, header


def test_require_user_401_without_cookie(probe_client):
    r = probe_client.get("/api/_probe/me")
    assert r.status_code == 401 and r.json() == {"error": "Vui lòng đăng nhập để tiếp tục"}


def test_valid_session_passes(probe_client, auth_db):
    u, _, _ = login_as(auth_db, probe_client)
    assert probe_client.get("/api/_probe/me").json() == {"id": u.id, "role": "customer"}


def test_expired_session_is_logged_out(probe_client, auth_db):
    _, token, _ = login_as(auth_db, probe_client)
    auth_db.execute(update(UserSession).where(UserSession.token_hash == sha256_hex(token))
                    .values(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
    auth_db.commit()
    assert probe_client.get("/api/_probe/me").status_code == 401


def test_unknown_token_is_logged_out(probe_client):
    probe_client.cookies.set(COOKIE, "khong-hop-le")
    assert probe_client.get("/api/_probe/me").status_code == 401


def test_role_forbidden_403(probe_client, auth_db):
    login_as(auth_db, probe_client, "customer")
    r = probe_client.get("/api/_probe/admin")
    assert r.status_code == 403 and r.json() == {"error": "Tài khoản của bạn không có quyền truy cập khu vực này"}


def test_role_requires_login_401(probe_client):
    assert probe_client.get("/api/_probe/admin").status_code == 401


def test_admin_allowed(probe_client, auth_db):
    login_as(auth_db, probe_client, "admin")
    assert probe_client.get("/api/_probe/admin").status_code == 200


def test_token_stored_hashed(probe_client, auth_db):
    u, token, _ = login_as(auth_db, probe_client)
    stored = set(auth_db.scalars(select(UserSession.token_hash).where(UserSession.user_id == u.id)))
    assert token not in stored and sha256_hex(token) in stored and len(token) >= 40


def test_cookie_attributes(probe_client, auth_db):
    _, _, header = login_as(auth_db, probe_client)
    h = header.lower()
    assert header.startswith(f"{COOKIE}=")
    assert "httponly" in h and "samesite=lax" in h and "path=/" in h and "max-age=2592000" in h
    assert "secure" not in h  # ENV=dev


def test_non_json_write_is_415(probe_client):
    r = probe_client.post("/api/_probe/echo", content="a=1", headers={"content-type": "application/x-www-form-urlencoded"})
    assert r.status_code == 415 and r.json() == {"error": "Yêu cầu phải gửi dạng JSON"}


def test_write_without_content_type_is_415(probe_client):
    assert probe_client.post("/api/_probe/echo").status_code == 415


def test_json_write_passes(probe_client):
    assert probe_client.post("/api/_probe/echo", json={}).status_code == 200
    r = probe_client.post("/api/_probe/echo", content="{}", headers={"content-type": "application/json; charset=utf-8"})
    assert r.status_code == 200


def test_body_over_20kb_is_413(probe_client):
    r = probe_client.post("/api/_probe/echo", content="{" + " " * (20 * 1024) + "}",
                          headers={"content-type": "application/json"})
    assert r.status_code == 413 and r.json() == {"error": "Dữ liệu gửi lên quá lớn"}


def test_body_at_limit_is_accepted(probe_client):
    body = "{" + " " * (20 * 1024 - 2) + "}"
    assert len(body) == 20 * 1024
    assert probe_client.post("/api/_probe/echo", content=body, headers={"content-type": "application/json"}).status_code == 200


def test_chunked_body_without_length_is_411(probe_client):
    def gen():
        yield b"{}"

    r = probe_client.post("/api/_probe/echo", content=gen(), headers={"content-type": "application/json"})
    assert r.status_code == 411 and r.json() == {"error": "Thiếu độ dài dữ liệu gửi lên (Content-Length)"}


def test_huge_login_password_rejected_before_parsing(c):
    r = c.post("/api/auth/login", content='{"identifier": "an@x.vn", "password": "' + "x" * 1_000_000 + '"}',
               headers={"content-type": "application/json"})
    assert r.status_code == 413
