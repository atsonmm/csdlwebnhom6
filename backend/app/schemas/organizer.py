"""Body request (Pydantic) của nhóm API organizer — tách từ routers/organizer.py"""
from typing import Any
from pydantic import BaseModel


class CheckinIn(BaseModel):
    code: Any = None

class CancelIn(BaseModel):
    reason: Any = None

class WithdrawalIn(BaseModel):
    amount: Any = None
    bankName: Any = None
    accountNo: Any = None
    accountName: Any = None

class DecideWithdrawalIn(BaseModel):
    decision: Any = None
    note: Any = None
