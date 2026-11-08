"""Chống dò mật khẩu: sai 5 lần → khoá 15 phút (theo từng cặp IP | email-hoặc-sđt).
Lưu trong bộ nhớ của tiến trình — giống bản Node; khởi động lại server thì xoá hết."""
import math
import threading
import time
from collections.abc import Callable
from datetime import timedelta

from fastapi import HTTPException


class LoginLimiter:
    def __init__(self, max_fails: int = 5, lock: timedelta = timedelta(minutes=15),
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.max_fails = max_fails
        self.lock_seconds = lock.total_seconds()
        self.clock = clock
        self._state: dict[str, list[float]] = {}  # key → [số lần sai, khoá đến (giây)]
        self._mutex = threading.Lock()

    def check(self, key: str) -> None:
        with self._mutex:
            fails_until = self._state.get(key)
            wait = (fails_until[1] - self.clock()) if fails_until else 0
        if wait > 0:
            mins = math.ceil(wait / 60)
            raise HTTPException(429, f"Bạn đã nhập sai quá nhiều lần. Vui lòng thử lại sau {mins} phút.")

    def fail(self, key: str) -> None:
        with self._mutex:
            state = self._state.setdefault(key, [0, 0.0])
            state[0] += 1
            if state[0] >= self.max_fails:
                state[0] = 0
                state[1] = self.clock() + self.lock_seconds

    def clear(self, key: str) -> None:
        with self._mutex:
            self._state.pop(key, None)


login_limiter = LoginLimiter()


def get_login_limiter() -> LoginLimiter:
    """Dependency — test thay bằng limiter có đồng hồ giả"""
    return login_limiter
