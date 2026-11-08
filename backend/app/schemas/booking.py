"""Body request (Pydantic) của nhóm API đặt vé"""
from typing import Any

from pydantic import BaseModel


class OrderIn(BaseModel):
    """Nhận mọi kiểu rồi tự kiểm tra, để câu báo lỗi giống hệt bản Node.
    Giá, tổng tiền, giảm giá client gửi lên đều bị bỏ qua — máy chủ tự tính."""

    slug: Any = ""
    showId: Any = ""
    items: Any = None
    seats: Any = None
    buyer: Any = None
    method: Any = ""
    coupon: Any = ""
