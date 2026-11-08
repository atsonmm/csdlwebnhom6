"""Kiểm tra dữ liệu tài khoản — cùng quy tắc và câu báo lỗi với server/auth.js của bản Node"""
import re
from typing import Any

from fastapi import HTTPException

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")
PHONE_RE = re.compile(r"^0(3|5|7|8|9)\d{8}$")
EMAIL_MAX = 254
PASSWORD_MIN, PASSWORD_MAX = 6, 128


def as_str(v: Any) -> str:
    """Giống str() của Node: không phải chuỗi thì coi là chuỗi rỗng"""
    return v if isinstance(v, str) else ""


def normalize_phone(v: Any) -> str:
    """"+84 912.345.678" → "0912345678" """
    return re.sub(r"^\+84", "0", re.sub(r"[\s.-]", "", as_str(v)))


def is_email(v: Any) -> bool:
    return bool(EMAIL_RE.match(as_str(v).strip()))


def is_phone(v: Any) -> bool:
    return bool(PHONE_RE.match(normalize_phone(v)))


def parse_identifier(v: Any) -> dict | None:
    """Email (chữ thường) hoặc số điện thoại (chuẩn hoá về 0xxxxxxxxx); sai định dạng → None"""
    s = as_str(v).strip()
    if "@" in s:
        email = s.lower()
        return {"email": email} if EMAIL_RE.match(email) and len(email) <= EMAIL_MAX else None
    phone = normalize_phone(s)
    return {"phone": phone} if PHONE_RE.match(phone) else None


def check_password(pw: str) -> None:
    if len(pw) < PASSWORD_MIN:
        raise HTTPException(400, f"Mật khẩu tối thiểu {PASSWORD_MIN} ký tự")
    if len(pw) > PASSWORD_MAX:
        raise HTTPException(400, f"Mật khẩu tối đa {PASSWORD_MAX} ký tự")
