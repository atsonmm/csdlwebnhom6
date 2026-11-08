"""Kiểm tra dữ liệu tài khoản — cùng quy tắc với server/auth.js"""
import pytest
from fastapi import HTTPException

from app.utils.validators import as_str, check_password, is_email, is_phone, normalize_phone, parse_identifier


@pytest.mark.parametrize("raw,expected", [
    (" An@X.VN ", {"email": "an@x.vn"}),
    ("+84 912.345.678", {"phone": "0912345678"}),
    ("0912-345-678", {"phone": "0912345678"}),
    ("0381234567", {"phone": "0381234567"}),
    ("0212345678", None),          # đầu số không hợp lệ
    ("091234567", None),           # thiếu số
    ("a@b.c", None),               # tên miền cấp cao < 2 ký tự
    ("a b@x.vn", None),
    ("", None),
    (123, None),
    (None, None),
    ("x" * 250 + "@a.vn", None),   # > 254 ký tự
])
def test_parse_identifier(raw, expected):
    assert parse_identifier(raw) == expected


@pytest.mark.parametrize("pw,msg", [("12345", "Mật khẩu tối thiểu 6 ký tự"), ("x" * 129, "Mật khẩu tối đa 128 ký tự")])
def test_check_password_messages(pw, msg):
    with pytest.raises(HTTPException) as e:
        check_password(pw)
    assert e.value.status_code == 400 and e.value.detail == msg


def test_check_password_accepts_6_to_128():
    check_password("123456")
    check_password("x" * 128)


def test_as_str():
    assert as_str(5) == "" and as_str(None) == "" and as_str(["a"]) == "" and as_str("a") == "a"


def test_phone_and_email_helpers():
    assert normalize_phone("+84 912.345.678") == "0912345678"
    assert is_phone("0912 345 678") and not is_phone("12345")
    assert is_email(" b@x.vn ") and not is_email("b@x")
