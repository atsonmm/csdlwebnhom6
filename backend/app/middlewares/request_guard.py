"""Middleware kiểm tra request ghi dữ liệu vào /api (JSON-only chống CSRF, giới hạn kích thước thân)"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
MAX_BODY_BYTES = 20 * 1024  # như express.json({ limit: '20kb' }) của bản Node


def _api_error(status: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": message})


async def json_only(request: Request, call_next):
    """Request ghi dữ liệu vào /api:
    - phải là JSON — cùng cookie SameSite=Lax giúp chống CSRF (form HTML của trang khác không gửi được JSON);
    - tối đa 20 KB và phải có Content-Length — chặn gửi thân dữ liệu khổng lồ làm cạn bộ nhớ / CPU."""
    if request.url.path.startswith("/api/") and request.method not in SAFE_METHODS:
        ctype = request.headers.get("content-type", "").lower()
        if not ctype.startswith("application/json"):
            return _api_error(415, "Yêu cầu phải gửi dạng JSON")
        length = request.headers.get("content-length")
        if length is None:
            if request.headers.get("transfer-encoding"):
                return _api_error(411, "Thiếu độ dài dữ liệu gửi lên (Content-Length)")
        elif not length.isdigit():
            return _api_error(400, "Dữ liệu gửi lên không hợp lệ")
        elif int(length) > MAX_BODY_BYTES:
            return _api_error(413, "Dữ liệu gửi lên quá lớn")
    return await call_next(request)


def install_request_guard(app: FastAPI) -> None:
    app.middleware("http")(json_only)
