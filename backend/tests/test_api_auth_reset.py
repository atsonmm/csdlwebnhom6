"""POST /api/auth/forgot, POST /api/auth/reset"""
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.middlewares.auth import sha256_hex
from app.main import app
from app.models.users import PasswordReset

FORGOT, RESET, LOGIN = "/api/auth/forgot", "/api/auth/reset", "/api/auth/login"
EXPIRED = {"error": "Liên kết đặt lại mật khẩu đã hết hạn hoặc không hợp lệ"}


@pytest.fixture
def registered(c):
    c.post("/api/auth/register", json={"name": "An", "identifier": "an@x.vn", "password": "matkhau1"})
    c.post("/api/auth/logout", json={})
    c.cookies.clear()


def reset_token(c) -> str:
    url = c.post(FORGOT, json={"identifier": "an@x.vn"}).json()["devResetUrl"]
    return parse_qs(urlparse(url).query)["reset"][0]


def test_forgot_same_shape_for_unknown_account(c):
    r = c.post(FORGOT, json={"identifier": "khongco@x.vn"})
    assert r.status_code == 200 and r.json() == {"ok": True}


def test_forgot_dev_returns_reset_url(c, registered):
    r = c.post(FORGOT, json={"identifier": " AN@X.VN "})
    body = r.json()
    assert r.status_code == 200 and body["ok"] is True
    assert "/?reset=" in body["devResetUrl"] and body["devResetUrl"].startswith("http")


def test_forgot_bad_identifier_400(c):
    r = c.post(FORGOT, json={"identifier": "abc"})
    assert r.status_code == 400 and r.json() == {"error": "Email hoặc số điện thoại không hợp lệ"}


def test_reset_token_stored_hashed_and_expires_in_15_minutes(c, registered, auth_db):
    token = reset_token(c)
    row = auth_db.scalar(select(PasswordReset).where(PasswordReset.token_hash == sha256_hex(token)))
    assert row is not None and row.used is False
    left = row.expires_at - datetime.now(timezone.utc)
    assert timedelta(minutes=14) < left <= timedelta(minutes=15)


def test_reset_changes_password_and_logs_in(c, registered):
    r = c.post(RESET, json={"token": reset_token(c), "password": "matkhaumoi"})
    assert r.status_code == 200 and r.json()["user"]["email"] == "an@x.vn"
    assert c.get("/api/auth/me").json()["user"]["email"] == "an@x.vn"
    other = TestClient(app)
    assert other.post(LOGIN, json={"identifier": "an@x.vn", "password": "matkhau1"}).status_code == 401
    assert other.post(LOGIN, json={"identifier": "an@x.vn", "password": "matkhaumoi"}).status_code == 200


def test_reset_invalidates_other_sessions(c, registered):
    other = TestClient(app)
    other.post(LOGIN, json={"identifier": "an@x.vn", "password": "matkhau1"})
    assert other.get("/api/auth/me").json()["user"] is not None
    c.post(RESET, json={"token": reset_token(c), "password": "matkhaumoi"})
    assert other.get("/api/auth/me").json() == {"user": None}


def test_reset_token_single_use(c, registered):
    token = reset_token(c)
    assert c.post(RESET, json={"token": token, "password": "matkhaumoi"}).status_code == 200
    r = c.post(RESET, json={"token": token, "password": "matkhaukhac"})
    assert r.status_code == 400 and r.json() == EXPIRED


def test_reset_token_expired(c, registered, auth_db):
    token = reset_token(c)
    auth_db.execute(update(PasswordReset).where(PasswordReset.token_hash == sha256_hex(token))
                    .values(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
    auth_db.commit()
    r = c.post(RESET, json={"token": token, "password": "matkhaumoi"})
    assert r.status_code == 400 and r.json() == EXPIRED


@pytest.mark.parametrize("token", ["", "khong-hop-le", None, 123])
def test_reset_invalid_token(c, token):
    r = c.post(RESET, json={"token": token, "password": "matkhaumoi"})
    assert r.status_code == 400 and r.json() == EXPIRED


def test_reset_short_password_400_and_token_still_usable(c, registered):
    token = reset_token(c)
    r = c.post(RESET, json={"token": token, "password": "123"})
    assert r.status_code == 400 and r.json() == {"error": "Mật khẩu tối thiểu 6 ký tự"}
    assert c.post(RESET, json={"token": token, "password": "matkhaumoi"}).status_code == 200


def test_parallel_resets_with_same_token_only_one_succeeds(c, registered):
    """Liên kết đặt lại chỉ dùng được 1 lần, kể cả khi nhiều yêu cầu đến cùng lúc"""
    from concurrent.futures import ThreadPoolExecutor

    token = reset_token(c)

    def attempt(i: int) -> int:
        return TestClient(app).post(RESET, json={"token": token, "password": f"matkhau-moi-{i}"}).status_code

    with ThreadPoolExecutor(max_workers=6) as pool:
        codes = list(pool.map(attempt, range(6)))
    assert sorted(codes) == [200] + [400] * 5


def test_prod_never_returns_dev_reset_url(c, registered, monkeypatch):
    from app.config.settings import settings

    monkeypatch.setattr(settings, "env", "prod")
    r = c.post(FORGOT, json={"identifier": "an@x.vn"})
    assert r.status_code == 200 and r.json() == {"ok": True}


def test_prod_session_cookie_is_secure(c, monkeypatch):
    from app.config.settings import settings

    monkeypatch.setattr(settings, "env", "prod")
    r = c.post("/api/auth/register", json={"name": "An", "identifier": "an@x.vn", "password": "matkhau1"})
    assert "secure" in r.headers["set-cookie"].lower()


def test_cookie_secure_override_for_plain_http_vm(c, monkeypatch):
    """Triển khai máy ảo chưa có HTTPS: COOKIE_SECURE=false bỏ cờ Secure dù ENV=prod (nếu không trình duyệt không gửi cookie)"""
    from app.config.settings import settings

    monkeypatch.setattr(settings, "env", "prod")
    monkeypatch.setattr(settings, "cookie_secure", False)
    r = c.post("/api/auth/register", json={"name": "An", "identifier": "an@x.vn", "password": "matkhau1"})
    assert r.status_code == 201 and "secure" not in r.headers["set-cookie"].lower()
