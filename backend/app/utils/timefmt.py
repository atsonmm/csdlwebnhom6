"""Định dạng thời gian trả ra API: luôn theo giờ Việt Nam (+07:00)"""
from datetime import datetime, time
from zoneinfo import ZoneInfo

VN = ZoneInfo("Asia/Ho_Chi_Minh")


def iso_vn(dt: datetime | None) -> str | None:
    """2026-11-15T12:00Z → "2026-11-15T19:00:00+07:00" """
    return None if dt is None else dt.astimezone(VN).isoformat(timespec="seconds")


def hhmm(value: datetime | time) -> str:
    """Giờ dạng "HH:MM" (datetime đổi sang giờ VN trước)"""
    if isinstance(value, datetime):
        value = value.astimezone(VN)
    return value.strftime("%H:%M")
