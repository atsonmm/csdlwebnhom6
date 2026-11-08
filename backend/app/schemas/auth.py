"""Body request (Pydantic) của nhóm API auth — tách từ routers/auth.py"""
from typing import Any
from pydantic import BaseModel


class RegisterIn(BaseModel):
    """Nhận mọi kiểu rồi tự kiểm tra, để câu báo lỗi giống hệt bản Node"""

    name: Any = ""
    identifier: Any = ""
    password: Any = ""

class LoginIn(BaseModel):
    identifier: Any = ""
    password: Any = ""

class ForgotIn(BaseModel):
    identifier: Any = ""

class ResetIn(BaseModel):
    token: Any = ""
    password: Any = ""
