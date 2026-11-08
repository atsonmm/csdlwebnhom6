"""POST /api/auth/login + khoá sau 5 lần sai (15 phút)"""
import pytest

from app.controllers import auth_controller
from app.main import app
from app.middlewares.ratelimit import LoginLimiter, get_login_limiter

LOGIN = "/api/auth/login"
RIGHT = {"identifier": "an@x.vn", "password": "matkhau1"}
WRONG = {"identifier": "an@x.vn", "password": "sai-mat-khau"}
BAD_CREDENTIALS = {"error": "Email/số điện thoại hoặc mật khẩu không đúng"}


class FakeClock:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t

    def advance(self, *, minutes: float = 0, seconds: float = 0) -> None:
        self.t += minutes * 60 + seconds


@pytest.fixture
def clock():
    fake = FakeClock()
    limiter = LoginLimiter(clock=fake)
    app.dependency_overrides[get_login_limiter] = lambda: limiter
    yield fake
    app.dependency_overrides.pop(get_login_limiter, None)


@pytest.fixture
def registered(c):
    c.post("/api/auth/register", json={"name": "An", "identifier": "an@x.vn", "password": "matkhau1"})
    c.post("/api/auth/register", json={"name": "Bình", "identifier": "0912345678", "password": "matkhau2"})
    c.post("/api/auth/logout", json={})
    c.cookies.clear()


def test_login_with_email_any_case(c, clock, registered):
    r = c.post(LOGIN, json={"identifier": " AN@X.VN ", "password": "matkhau1"})
    assert r.status_code == 200 and r.json()["user"]["email"] == "an@x.vn"
    assert c.get("/api/auth/me").json()["user"]["email"] == "an@x.vn"


def test_login_with_phone_any_format(c, clock, registered):
    r = c.post(LOGIN, json={"identifier": "+84 912 345 678", "password": "matkhau2"})
    assert r.status_code == 200 and r.json()["user"]["phone"] == "0912345678"


def test_wrong_password_and_unknown_user_same_401(c, clock, registered):
    r1 = c.post(LOGIN, json=WRONG)
    r2 = c.post(LOGIN, json={"identifier": "khongco@x.vn", "password": "sai-mat-khau"})
    assert r1.status_code == r2.status_code == 401
    assert r1.json() == r2.json() == BAD_CREDENTIALS
    assert c.get("/api/auth/me").json() == {"user": None}


@pytest.mark.parametrize("body", [{}, {"identifier": "an@x.vn"}, {"identifier": "abc", "password": "x"},
                                  {"identifier": "an@x.vn", "password": ""}, {"identifier": 5, "password": 5}])
def test_missing_or_bad_fields_400(c, clock, body):
    r = c.post(LOGIN, json=body)
    assert r.status_code == 400 and r.json() == {"error": "Vui lòng nhập email/số điện thoại và mật khẩu"}


def test_fifth_failure_locks_for_15_minutes(c, clock, registered):
    for _ in range(4):
        assert c.post(LOGIN, json=WRONG).status_code == 401
    assert c.post(LOGIN, json=WRONG).status_code == 401  # lần thứ 5: vẫn 401, nhưng từ giờ bị khoá
    r = c.post(LOGIN, json=RIGHT)                        # khoá cả khi mật khẩu đúng
    assert r.status_code == 429
    assert r.json() == {"error": "Bạn đã nhập sai quá nhiều lần. Vui lòng thử lại sau 15 phút."}
    clock.advance(minutes=14, seconds=1)
    assert c.post(LOGIN, json=RIGHT).json() == {"error": "Bạn đã nhập sai quá nhiều lần. Vui lòng thử lại sau 1 phút."}
    clock.advance(minutes=1)
    assert c.post(LOGIN, json=RIGHT).status_code == 200


def test_success_resets_fail_counter(c, clock, registered):
    for _ in range(4):
        c.post(LOGIN, json=WRONG)
    assert c.post(LOGIN, json=RIGHT).status_code == 200
    for _ in range(4):
        assert c.post(LOGIN, json=WRONG).status_code == 401
    assert c.post(LOGIN, json=RIGHT).status_code == 200


def test_lock_is_per_identifier(c, clock, registered):
    for _ in range(5):
        c.post(LOGIN, json=WRONG)
    assert c.post(LOGIN, json=RIGHT).status_code == 429
    assert c.post(LOGIN, json={"identifier": "0912345678", "password": "matkhau2"}).status_code == 200


def test_same_account_any_format_shares_lock(c, clock, registered):
    for _ in range(5):
        c.post(LOGIN, json={"identifier": "0912345678", "password": "sai"})
    assert c.post(LOGIN, json={"identifier": "+84 912 345 678", "password": "matkhau2"}).status_code == 429


def test_unknown_user_still_runs_scrypt(c, clock, monkeypatch):
    calls = []
    real = auth_controller.verify_password
    monkeypatch.setattr(auth_controller, "verify_password", lambda pw, h: calls.append(h) or real(pw, h))
    c.post(LOGIN, json={"identifier": "khongco@x.vn", "password": "matkhau1"})
    assert len(calls) == 1 and calls[0].startswith("scrypt$")
