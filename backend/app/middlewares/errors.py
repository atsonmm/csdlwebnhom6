"""Xử lý lỗi tập trung: mọi lỗi trả về {"error": "<câu tiếng Việt>"} như API Node cũ"""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("ticketnhip")

DB_DOWN = "Không kết nối được CSDL. Kiểm tra PostgreSQL đang chạy và DATABASE_URL."
NOT_FOUND_API = "Không tìm thấy API"
BAD_INPUT = "Dữ liệu gửi lên không hợp lệ"
SERVER_ERROR = "Lỗi máy chủ, vui lòng thử lại sau"
WRONG_METHOD = "Phương thức không được hỗ trợ cho API này"
BUSY_RETRY = "Hệ thống đang bận, vui lòng thử lại"


def not_found(message: str) -> HTTPException:
    return HTTPException(status_code=404, detail=message)


def _error(status: int, message: str, headers: dict | None = None) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": message}, headers=headers)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_error(_req: Request, exc: StarletteHTTPException) -> JSONResponse:
        # 404 của bộ định tuyến (không có route) mang detail mặc định "Not Found"
        headers = getattr(exc, "headers", None)  # vd. Allow của 405
        if exc.status_code == 404 and exc.detail == "Not Found":
            return _error(404, NOT_FOUND_API, headers)
        if exc.status_code == 405:
            return _error(405, WRONG_METHOD, headers)
        return _error(exc.status_code, str(exc.detail), headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_req: Request, _exc: RequestValidationError) -> JSONResponse:
        return _error(400, BAD_INPUT)

    @app.exception_handler(OperationalError)
    async def db_operational(_req: Request, exc: OperationalError) -> JSONResponse:
        # Phân loại theo SQLSTATE của PostgreSQL:
        #   không có mã (lỗi phía client, vd. hết thời gian kết nối), 08 (kết nối), 28 (xác thực),
        #   57P (máy chủ tắt / chưa sẵn sàng)  → 503 "không kết nối được CSDL"
        #   40 (giao dịch bị huỷ: deadlock, xung đột tuần tự hoá — gặp khi đặt vé)  → 409 "thử lại"
        #   còn lại → 500
        state = getattr(exc.orig, "sqlstate", None)
        if exc.connection_invalidated or state is None or state.startswith(("08", "28", "57P")):
            return _error(503, DB_DOWN)
        if state.startswith("40"):
            return _error(409, BUSY_RETRY)
        log.exception("Lỗi CSDL", exc_info=exc)
        return _error(500, SERVER_ERROR)

    @app.exception_handler(Exception)
    async def unhandled(_req: Request, exc: Exception) -> JSONResponse:
        log.exception("Lỗi chưa xử lý", exc_info=exc)
        return _error(500, SERVER_ERROR)
