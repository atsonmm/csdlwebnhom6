"""POST /api/organizer/register, GET /api/organizer/me"""
import pytest
from sqlalchemy import select

from app.models.users import Organizer

REG = "/api/organizer/register"
OK = {"orgName": "  Công ty ABC  ", "phone": "+84 912 345 678", "description": "Chuyên tổ chức hoà nhạc"}


def test_register_turns_customer_into_organizer(c, logged_customer, api_db):
    r = c.post(REG, json=OK)
    assert r.status_code == 201 and r.json()["user"]["role"] == "organizer"
    assert c.get("/api/auth/me").json()["user"]["role"] == "organizer"
    api_db.expire_all()
    org = api_db.get(Organizer, logged_customer.id)
    assert org.org_name == "Công ty ABC" and org.phone == "0912345678" and org.description == "Chuyên tổ chức hoà nhạc"


def test_register_again_updates_profile(c, logged_customer, api_db):
    c.post(REG, json=OK)
    assert c.post(REG, json=OK | {"orgName": "Công ty XYZ"}).status_code == 201
    api_db.expire_all()
    assert api_db.scalars(select(Organizer.org_name).where(Organizer.user_id == logged_customer.id)).all() == ["Công ty XYZ"]


@pytest.mark.parametrize("patch,msg", [
    ({"orgName": "A"}, "Vui lòng nhập tên đơn vị tổ chức (2–120 ký tự)"),
    ({"orgName": "x" * 121}, "Vui lòng nhập tên đơn vị tổ chức (2–120 ký tự)"),
    ({"orgName": None}, "Vui lòng nhập tên đơn vị tổ chức (2–120 ký tự)"),
    ({"phone": "123"}, "Số điện thoại liên hệ không hợp lệ"),
    ({"description": "x" * 1001}, "Giới thiệu tối đa 1000 ký tự"),
])
def test_register_validation(c, logged_customer, patch, msg):
    r = c.post(REG, json=OK | patch)
    assert r.status_code == 400 and r.json() == {"error": msg}


def test_admin_cannot_register(c, logged_admin):
    r = c.post(REG, json=OK)
    assert r.status_code == 400 and r.json() == {"error": "Tài khoản quản trị không thể đăng ký làm Ban tổ chức"}


def test_register_requires_login(api, c):
    assert c.post(REG, json=OK).status_code == 401


def test_me_requires_organizer_role(c, logged_customer):
    r = c.get("/api/organizer/me")
    assert r.status_code == 403 and r.json() == {"error": "Tài khoản của bạn không có quyền truy cập khu vực này"}


def test_me_requires_login(api, c):
    assert c.get("/api/organizer/me").status_code == 401


def test_me_empty_shape(c, logged_organizer):
    body = c.get("/api/organizer/me").json()
    org = body["organizer"]
    assert org["code"] == f"ORG-{logged_organizer.id:05d}"
    assert org["orgName"] == "Công ty Sự kiện Thử" and org["phone"] == "0987654321" and org["description"] is None
    assert org["createdAt"].endswith("+07:00")
    assert body["events"] == [] and body["recentOrders"] == []
