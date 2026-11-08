"""Body request (Pydantic) của nhóm API manage — tách từ routers/manage.py"""
from typing import Any
from pydantic import BaseModel


class OrganizerIn(BaseModel):
    orgName: Any = ""
    phone: Any = ""
    description: Any = ""

class ReviewIn(BaseModel):
    decision: Any = ""
    reason: Any = ""


class OrgEventIn(BaseModel):
    title: Any = ""
    category: Any = ""
    city: Any = ""
    venue: Any = ""
    address: Any = ""
    date: Any = ""
    startTime: Any = ""
    endTime: Any = ""
    description: Any = ""
    tiers: Any = None  # [{id?, name, price, quantity, perks}] — id chỉ dùng khi sửa (hạng cũ)
    saleStart: Any = ""  # "YYYY-MM-DDTHH:mm" giờ VN, không bắt buộc
    layout: Any = ""  # "list" (mặc định) | "zones" | "seats" (Task F1: bán theo sơ đồ có sẵn)
    mapId: Any = None  # mã sơ đồ khi layout là zones / seats
    prices: Any = None  # {mã nhóm: giá} khi bán theo sơ đồ; tiers bị bỏ qua
