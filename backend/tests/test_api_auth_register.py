"""POST /api/auth/register, GET /api/auth/me, POST /api/auth/logout"""
import pytest
from sqlalchemy import select

from app.middlewares.auth import COOKIE, sha256_hex
from app.models.users import User, UserSession
from app.utils.security import verify_password

REG = "/api/auth/register"
OK = {"name": " Nguyễn An ", "identifier": " An@X.VN ", "password": "matkhau1"}


def test_register_email_creates_user_and_logs_in(c):
    r = c.post(REG, json=OK)
    assert r.status_code == 201
    user = r.json()["user"]
    assert user | {"id": 0} == {"id": 0, "name": "Nguyễn An", "email": "an@x.vn", "phone": None, "role": "customer"}
    assert c.get("/api/auth/me").json()["user"]["email"] == "an@x.vn"


def test_register_phone_normalized(c):
    r = c.post(REG, json={"name": "Bình", "identifier": "+84 912.345.678", "password": "matkhau1"})
    assert r.status_code == 201 and r.json()["user"]["phone"] == "0912345678" and r.json()["user"]["email"] is None


def test_register_duplicate_email_case_insensitive_409(c):
    c.post(REG, json=OK)
    r = c.post(REG, json=OK | {"identifier": "AN@x.vn"})
    assert r.status_code == 409 and r.json() == {"error": "Email này đã được đăng ký"}


def test_register_duplicate_phone_any_format_409(c):
    c.post(REG, json={"name": "Bình", "identifier": "0912345678", "password": "matkhau1"})
    r = c.post(REG, json={"name": "Bình 2", "identifier": "+84 912 345 678", "password": "matkhau1"})
    assert r.status_code == 409 and r.json() == {"error": "Số điện thoại này đã được đăng ký"}


@pytest.mark.parametrize("patch,msg", [
    ({"name": "A"}, "Vui lòng nhập họ và tên (2–80 ký tự)"),
    ({"name": "x" * 81}, "Vui lòng nhập họ và tên (2–80 ký tự)"),
    ({"name": 123}, "Vui lòng nhập họ và tên (2–80 ký tự)"),
    ({"identifier": "abc"}, "Email hoặc số điện thoại không hợp lệ"),
    ({"identifier": None}, "Email hoặc số điện thoại không hợp lệ"),
    ({"password": "123"}, "Mật khẩu tối thiểu 6 ký tự"),
    ({"password": 12345678}, "Mật khẩu tối thiểu 6 ký tự"),
])
def test_register_validation_messages(c, patch, msg):
    r = c.post(REG, json=OK | patch)
    assert r.status_code == 400 and r.json() == {"error": msg}


def test_register_empty_body_object(c):
    r = c.post(REG, json={})
    assert r.status_code == 400 and r.json() == {"error": "Vui lòng nhập họ và tên (2–80 ký tự)"}


def test_password_stored_as_scrypt(c, auth_db):
    c.post(REG, json=OK)
    h = auth_db.scalar(select(User.password_hash).where(User.email == "an@x.vn"))
    assert h.startswith("scrypt$") and verify_password("matkhau1", h)


def test_me_anonymous_is_null(c):
    r = c.get("/api/auth/me")
    assert r.status_code == 200 and r.json() == {"user": None}


def test_logout_clears_cookie_and_session(c, auth_db):
    c.post(REG, json=OK)
    token = c.cookies.get(COOKIE)
    r = c.post("/api/auth/logout", json={})
    assert r.status_code == 200 and r.json() == {"ok": True}
    assert c.get("/api/auth/me").json() == {"user": None}
    assert auth_db.scalar(select(UserSession).where(UserSession.token_hash == sha256_hex(token))) is None


def test_logout_when_anonymous_is_ok(c):
    assert c.post("/api/auth/logout", json={}).json() == {"ok": True}


def test_malformed_json_400(c):
    r = c.post(REG, content="{", headers={"content-type": "application/json"})
    assert r.status_code == 400 and r.json() == {"error": "Dữ liệu gửi lên không hợp lệ"}


def test_non_object_json_400(c):
    r = c.post(REG, json=["a"])
    assert r.status_code == 400 and r.json() == {"error": "Dữ liệu gửi lên không hợp lệ"}
